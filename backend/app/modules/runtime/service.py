import asyncio
import json
import time
from collections.abc import AsyncIterator
from datetime import timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.core.errors import APIError
from app.models import Message
from app.modules.capabilities.schemas import CapabilitySnapshot
from app.modules.capabilities.models import (
    CapabilityDefinition,
    CapabilityDependency,
    CapabilityVersion,
)
from app.modules.capabilities.service import CapabilityService, loads
from app.modules.identity.user_service import UserPrincipal
from app.modules.personal.service import PersonalService, decrypt_secret
from app.modules.personal.models import PersonalSkill
from app.modules.personal.models import McpConnection, McpServer
from app.modules.runtime.models import AgentRun, RunStep, RunTrace
from app.modules.runtime.providers import build_provider
from app.modules.runtime.mcp_client import McpClient, validate_mcp_url
from app.modules.runtime.tools import execute_tool, get_tool
from app.repositories import OwnerScope, utc_now
from app.schemas import ExecutionStep, MessagePatch, TurnCreate
from app.services import ConversationService

MAX_OUTPUT_BYTES = 100_000


def run_view(run: AgentRun) -> dict[str, Any]:
    return {
        "id": run.id,
        "status": run.status,
        "mode": run.mode,
        "provider": run.provider,
        "capabilityId": run.capability_id,
        "versionId": run.version_id,
        "outputText": run.output_text,
        "errorCode": run.error_code,
        "errorMessage": run.error_message,
        "tokenInput": run.token_input,
        "tokenOutput": run.token_output,
        "stepCount": run.step_count,
        "createdAt": run.created_at.replace(tzinfo=timezone.utc),
        "startedAt": run.started_at.replace(tzinfo=timezone.utc) if run.started_at else None,
        "finishedAt": run.finished_at.replace(tzinfo=timezone.utc) if run.finished_at else None,
        "steps": [
            {
                "id": step.id,
                "seq": step.seq,
                "type": step.step_type,
                "name": step.name,
                "status": step.status,
                "input": loads(step.input_json, {}),
                "output": loads(step.output_json, {}),
                "error": step.error,
                "durationMs": step.duration_ms,
            }
            for step in run.steps
        ],
        "traces": [
            {
                "seq": trace.seq,
                "event": trace.event,
                "detail": loads(trace.detail_json, {}),
                "createdAt": trace.created_at.replace(tzinfo=timezone.utc),
            }
            for trace in run.traces
        ],
    }


class RuntimeService:
    def __init__(self, session: Session):
        self.session = session
        self.sequence = 0
        self.step_sequence = 0

    # ------------------------------------------------------------------ helpers
    def _check_quota(self, user_id: str) -> None:
        since = utc_now().replace(hour=0, minute=0, second=0, microsecond=0)
        count = self.session.scalar(
            select(func.count(AgentRun.id)).where(
                AgentRun.user_id == user_id, AgentRun.created_at >= since
            )
        )
        if (count or 0) >= settings.llm_daily_request_limit:
            raise APIError(429, "RUN_QUOTA_EXCEEDED", "今日执行额度已用完")

    def _trace(self, run: AgentRun, event: str, detail: dict[str, Any] | None = None) -> None:
        self.sequence += 1
        self.session.add(
            RunTrace(
                run_id=run.id,
                seq=self.sequence,
                event=event,
                detail_json=json.dumps(detail or {}, ensure_ascii=False, separators=(",", ":")),
                created_at=utc_now(),
            )
        )

    def _step(
        self,
        run: AgentRun,
        step_type: str,
        name: str,
        *,
        status: str,
        input_value: dict[str, Any],
        output: dict[str, Any],
        started_at,
        error: str = "",
    ) -> RunStep:
        finished = utc_now()
        duration = int((finished - started_at).total_seconds() * 1000)
        self.step_sequence += 1
        step = RunStep(
            run_id=run.id,
            seq=self.step_sequence,
            step_type=step_type,
            name=name,
            status=status,
            input_json=json.dumps(input_value, ensure_ascii=False, separators=(",", ":")),
            output_json=json.dumps(output, ensure_ascii=False, separators=(",", ":"))[
                :MAX_OUTPUT_BYTES
            ],
            error=error[:500],
            started_at=started_at,
            finished_at=finished,
            duration_ms=duration,
        )
        self.session.add(step)
        self.session.flush()
        run.step_count = self.step_sequence
        return step

    def create_run(
        self,
        principal: UserPrincipal,
        *,
        conversation_id: str,
        version_id: str,
        capability_id: str,
        input_text: str,
        mode: str | None = None,
    ) -> AgentRun:
        self._check_quota(principal.user.id)
        now = utc_now()
        configured_provider = settings.llm_provider.strip().lower() or "unconfigured"
        if configured_provider in {"fake", "test"}:
            configured_provider = "fake"
        run = AgentRun(
            user_id=principal.user.id,
            conversation_id=conversation_id,
            capability_id=capability_id,
            version_id=version_id,
            mode=configured_provider,
            provider=configured_provider,
            status="running",
            input_text=input_text[:6000],
            created_at=now,
            started_at=now,
        )
        self.session.add(run)
        self.session.flush()
        self.sequence = 0
        self.step_sequence = 0
        self._trace(run, "run.started", {"mode": mode, "capabilityId": capability_id})
        self.session.commit()
        return run

    async def stream(
        self,
        run: AgentRun,
        *,
        principal: UserPrincipal,
        scope: OwnerScope,
        assistant_message_id: str,
        payload: TurnCreate,
    ) -> AsyncIterator[dict[str, Any]]:
        output = ""
        capability_snapshot: CapabilitySnapshot | None = None
        yield {"type": "run", "runId": run.id}
        try:
            capability_snapshot, agent_event = self._prepare_run(
                run, principal, payload
            )
        except APIError as error:
            self._fail_run(run, scope, assistant_message_id, error)
            yield {
                "type": "error",
                "runId": run.id,
                "code": error.code,
                "message": error.message,
            }
            return
        if agent_event is not None:
            yield agent_event
        try:
            messages: list[dict[str, str]] = []
            if capability_snapshot is not None:
                instruction = capability_snapshot.content or capability_snapshot.description
                messages.append(
                    {
                        "role": "system",
                        "content": f"能力：{capability_snapshot.name}\n{instruction}"[:6000],
                    }
                )
            history = list(
                self.session.scalars(
                    select(Message)
                    .where(
                        Message.conversation_id == run.conversation_id,
                        Message.role.in_(("user", "assistant")),
                        Message.status.in_(("complete", "generating")),
                    )
                    .order_by(Message.seq.desc())
                    .limit(20)
                )
            )
            for item in reversed(history):
                if item.content:
                    messages.append({"role": item.role, "content": item.content[:6000]})
            if not messages or messages[-1]["content"] != payload.text:
                messages.append({"role": "user", "content": payload.text})

            tool_result: dict[str, Any] | None = None
            config = capability_snapshot.config if capability_snapshot else {}
            tool_name = str(config.get("tool", "")).strip()
            if tool_name:
                started = utc_now()
                self._trace(run, "tool.started", {"name": tool_name})
                try:
                    tool_result = execute_tool(
                        tool_name,
                        payload.model_dump().get("toolArguments")
                        or self._default_tool_arguments(tool_name, payload.text),
                        session=self.session,
                        user_id=principal.user.id,
                    )
                    self._step(
                        run,
                        "tool",
                        tool_name,
                        status="completed",
                        input_value={"text": payload.text},
                        output=tool_result,
                        started_at=started,
                    )
                    self._trace(run, "tool.completed", {"name": tool_name})
                    messages.append(
                        {"role": "tool", "content": json.dumps(tool_result, ensure_ascii=False)}
                    )
                    yield {"type": "tool", "name": tool_name, "result": tool_result}
                except APIError as error:
                    self._step(
                        run,
                        "tool",
                        tool_name,
                        status="failed",
                        input_value={},
                        output={},
                        started_at=started,
                        error=error.code,
                    )
                    raise
            elif str(config.get("executor", "")).strip().lower() == "mcp":
                mcp_started = utc_now()
                mcp_tool = str(config.get("mcpTool", "")).strip()
                server_id = str(config.get("mcpServerId", "")).strip()
                self._trace(run, "mcp.started", {"serverId": server_id, "tool": mcp_tool})
                try:
                    mcp_result = await self._call_mcp(
                        principal,
                        server_id=server_id,
                        tool_name=mcp_tool,
                        arguments=payload.model_dump().get("toolArguments") or {},
                    )
                    self._step(
                        run,
                        "mcp",
                        f"{server_id}:{mcp_tool}",
                        status="completed",
                        input_value={"tool": mcp_tool},
                        output=mcp_result,
                        started_at=mcp_started,
                    )
                    self._trace(run, "mcp.completed", {"tool": mcp_tool})
                    messages.append(
                        {
                            "role": "tool",
                            "content": json.dumps(mcp_result, ensure_ascii=False)[:8000],
                        }
                    )
                    yield {
                        "type": "mcp",
                        "serverId": server_id,
                        "name": mcp_tool,
                        "result": mcp_result,
                    }
                except APIError as error:
                    self._step(
                        run,
                        "mcp",
                        f"{server_id}:{mcp_tool}",
                        status="failed",
                        input_value={"tool": mcp_tool},
                        output={},
                        started_at=mcp_started,
                        error=error.code,
                    )
                    raise

            provider = build_provider()
            self._ensure_capability_allowed(run, principal)
            llm_started = utc_now()
            self._trace(run, "llm.started", {"provider": provider.name})
            self.session.commit()
            async with asyncio.timeout(settings.llm_timeout_seconds):
                async for chunk in provider.stream(messages):
                    if chunk.done:
                        run.token_input = max(run.token_input, chunk.token_input)
                        run.token_output = max(run.token_output, chunk.token_output)
                        break
                    output += chunk.text
                    if len(output.encode("utf-8")) > MAX_OUTPUT_BYTES:
                        raise APIError(422, "RUN_OUTPUT_TOO_LARGE", "模型输出超过限制")
                    yield {"type": "chunk", "content": chunk.text}
                    self.session.refresh(run)
                    if run.cancel_requested:
                        raise asyncio.CancelledError()
            run.output_text = output
            self._step(
                run,
                "llm",
                provider.name,
                status="completed",
                input_value={"messages": len(messages)},
                output={"chars": len(output)},
                started_at=llm_started,
            )
            self._trace(run, "llm.completed", {"chars": len(output)})
            run.status = "completed"
            run.finished_at = utc_now()
            ConversationService(self.session).patch_message(
                scope,
                run.conversation_id,
                assistant_message_id,
                MessagePatch(
                    content=output,
                    status="complete",
                    steps=[
                        ExecutionStep(
                            title="执行完成",
                            detail=f"{run.provider} 返回 {len(output)} 字符",
                        )
                    ],
                ),
                internal=True,
            )
            self._trace(run, "run.completed", {"status": "completed"})
            self.session.commit()
            yield {"type": "done", "runId": run.id, "status": "completed"}
        except asyncio.CancelledError:
            run.status = "cancelled"
            run.finished_at = utc_now()
            self._trace(run, "run.cancelled")
            ConversationService(self.session).patch_message(
                scope,
                run.conversation_id,
                assistant_message_id,
                MessagePatch(content=output, status="stopped", steps=[]),
                internal=True,
            )
            self.session.commit()
            yield {"type": "done", "runId": run.id, "status": "cancelled"}
        except TimeoutError:
            run.status = "timed_out"
            run.error_code = "RUN_TIMEOUT"
            run.error_message = "执行超时"
            run.finished_at = utc_now()
            self._trace(run, "run.timed_out")
            ConversationService(self.session).patch_message(
                scope,
                run.conversation_id,
                assistant_message_id,
                MessagePatch(content=output or "执行超时", status="error", steps=[]),
                internal=True,
            )
            self.session.commit()
            yield {"type": "error", "runId": run.id, "code": "RUN_TIMEOUT"}
        except APIError as error:
            self._fail_run(run, scope, assistant_message_id, error)
            yield {
                "type": "error",
                "runId": run.id,
                "code": error.code,
                "message": error.message,
            }
        except Exception as error:
            self.session.rollback()
            run = self.session.get(AgentRun, run.id)
            if run is not None:
                run.status = "failed"
                run.error_code = "RUN_INTERNAL_ERROR"
                run.error_message = str(error)[:500]
                run.finished_at = utc_now()
                self.session.commit()
            yield {
                "type": "error",
                "runId": run.id if run else "",
                "code": "RUN_INTERNAL_ERROR",
            }

    def _prepare_run(
        self,
        run: AgentRun,
        principal: UserPrincipal,
        payload: TurnCreate,
    ) -> tuple[CapabilitySnapshot | None, dict[str, Any] | None]:
        self._ensure_capability_allowed(run, principal)
        capability_snapshot: CapabilitySnapshot | None = None
        if run.capability_id:
            try:
                definition, version, _ = CapabilityService(self.session).resolve_published(
                    run.capability_id,
                    payload.capability.kind if payload.capability else None,
                )
                capability_snapshot = CapabilitySnapshot.model_validate(
                    loads(version.snapshot_json, {})
                )
                run.version_id = version.id
            except Exception:
                personal = self.session.scalar(
                    select(PersonalSkill).where(
                        PersonalSkill.id == run.capability_id,
                        PersonalSkill.user_id == principal.user.id,
                    )
                )
                if personal is not None:
                    capability_snapshot = CapabilitySnapshot(
                        kind="skill",
                        name=personal.name,
                        description=personal.description,
                        category="个人技能",
                        icon="skill",
                        steps=[],
                        tools=[],
                        content=personal.content_md,
                        config={},
                        executionMode="simulated",
                        source="managed",
                    )
        if capability_snapshot is None or capability_snapshot.kind != "agent":
            return capability_snapshot, None
        dependencies = list(
            self.session.scalars(
                select(CapabilityDependency).where(
                    CapabilityDependency.version_id == run.version_id
                )
            )
        )
        if not dependencies:
            raise APIError(
                409,
                "AGENT_DEPENDENCY_MISSING",
                "Agent 未锁定任何依赖版本",
            )
        resolved: list[dict[str, Any]] = []
        for dependency in dependencies:
            target = self.session.get(
                CapabilityVersion, dependency.dependency_version_id
            )
            target_definition = self.session.get(
                CapabilityDefinition, dependency.dependency_id
            )
            if (
                target is None
                or target.status != "published"
                or target_definition is None
                or target_definition.status != "published"
            ):
                raise APIError(
                    409,
                    "AGENT_DEPENDENCY_UNAVAILABLE",
                    "Agent 锁定依赖不可用",
                )
            resolved.append(
                {
                    "id": dependency.dependency_id,
                    "kind": dependency.dependency_kind,
                    "versionId": dependency.dependency_version_id,
                    "version": target.version,
                    "name": target_definition.name,
                }
            )
        self._step(
            run,
            "agent",
            "dependencies",
            status="completed",
            input_value={"versionId": run.version_id},
            output={"dependencies": resolved},
            started_at=utc_now(),
        )
        self._trace(run, "agent.dependencies", {"dependencies": resolved})
        return capability_snapshot, {"type": "agent", "dependencies": resolved}

    def _fail_run(
        self,
        run: AgentRun,
        scope: OwnerScope,
        assistant_message_id: str,
        error: APIError,
    ) -> None:
        run.status = "failed"
        run.error_code = error.code
        run.error_message = error.message[:500]
        run.finished_at = utc_now()
        self._trace(run, "run.failed", {"code": error.code})
        try:
            ConversationService(self.session).patch_message(
                scope,
                run.conversation_id,
                assistant_message_id,
                MessagePatch(
                    content=f"执行失败：{error.message}",
                    status="error",
                    steps=[],
                ),
                internal=True,
            )
        except Exception:
            pass
        self.session.commit()

    def _default_tool_arguments(self, tool_name: str, text: str) -> dict[str, Any]:
        tool = get_tool(tool_name)
        if tool is None:
            return {}
        if "query" in tool.schema.get("properties", {}):
            return {"query": text[:80], "limit": 5}
        return {}

    def _ensure_capability_allowed(
        self, run: AgentRun, principal: UserPrincipal
    ) -> None:
        if not run.capability_id:
            return
        personal = self.session.scalar(
            select(PersonalSkill).where(
                PersonalSkill.id == run.capability_id,
                PersonalSkill.user_id == principal.user.id,
            )
        )
        if personal is not None:
            return
        definition = self.session.get(CapabilityDefinition, run.capability_id)
        if definition is None or not CapabilityService(self.session).can_execute(
            definition, principal.user.id
        ):
            raise APIError(
                403,
                "CAPABILITY_REVOKED",
                "能力已停用、未发布或授权已撤销",
            )

    async def _call_mcp(
        self,
        principal: UserPrincipal,
        *,
        server_id: str,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        if not server_id or not tool_name:
            raise APIError(422, "MCP_CONFIG_INVALID", "MCP Server 或工具未配置")
        server = self.session.get(McpServer, server_id)
        if server is None or server.status != "approved":
            raise APIError(403, "MCP_SERVER_NOT_APPROVED", "MCP Server 未获平台批准")
        connection = self.session.scalar(
            select(McpConnection).where(
                McpConnection.user_id == principal.user.id,
                McpConnection.server_id == server.id,
                McpConnection.status == "connected",
            )
        )
        if connection is None:
            raise APIError(403, "MCP_CONNECTION_REQUIRED", "请先建立个人 MCP 授权")
        token = (
            decrypt_secret(connection.credential_ciphertext)
            if connection.credential_ciphertext
            else None
        )
        validate_mcp_url(server.endpoint_url)
        client = McpClient(server.endpoint_url, token=token, timeout=20)
        async with asyncio.timeout(25):
            result = await client.call_tool(tool_name, arguments)
        connection.last_used_at = utc_now()
        return result
