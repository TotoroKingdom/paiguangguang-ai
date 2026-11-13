import asyncio
import json
from datetime import timedelta

from sqlalchemy import select

from app.core.security import hash_user_password
from app.db import SessionLocal
from app.models import Conversation, Message
from app.modules.capabilities.schemas import CapabilitySnapshot
from app.modules.identity.models import User
from app.modules.runtime import service as runtime_service_module
from app.modules.runtime.models import AgentRun, RunMessage, RunStep
from app.modules.runtime.providers import LLMChunk
from app.modules.runtime.router import _wait_for_background_run
from app.modules.runtime.service import RuntimeService
from app.modules.runtime.worker import recover_expired_runs
from app.repositories import utc_now
from app.schemas import MessageRequest, TurnCreate


def _seed_recoverable_run():
    from app.modules.capabilities.models import (
        CapabilityDefinition,
        CapabilityDependency,
        CapabilityGrant,
        CapabilityVersion,
    )

    now = utc_now()
    with SessionLocal() as session:
        user = User(
            account_number="s2-recovery-user",
            password_hash=hash_user_password("s2-recovery-password"),
            nickname="Recovery",
            role="USER",
            status="ACTIVE",
            version=1,
            authz_version=1,
            created_at=now,
            updated_at=now,
            activated_at=now,
        )
        session.add(user)
        session.flush()
        conversation = Conversation(
            owner_id=user.id,
            user_id=user.id,
            title="Recovery",
            created_at=now,
            updated_at=now,
            version=2,
        )
        session.add(conversation)
        session.flush()
        request = MessageRequest(
            conversationId=conversation.id,
            clientTurnId="recovery-turn",
            text="recover tools",
            fileIds=[],
        )
        user_message = Message(
            conversation_id=conversation.id,
            seq=1,
            client_turn_id="recovery-turn",
            role="user",
            content=request.text,
            status="complete",
            steps_json="[]",
            capability_json="null",
            attachments_json="[]",
            request_json=request.model_dump_json(by_alias=True),
            created_at=now,
            updated_at=now,
        )
        assistant = Message(
            conversation_id=conversation.id,
            seq=2,
            client_turn_id=None,
            role="assistant",
            content="",
            status="generating",
            steps_json="[]",
            capability_json="null",
            attachments_json="[]",
            request_json=request.model_dump_json(by_alias=True),
            created_at=now,
            updated_at=now,
        )
        session.add_all([user_message, assistant])
        tool_definitions = []
        for slug, name, tool_name, access_mode in (
            ("recovery-time", "Recovery time", "system.current_time", "all_active"),
            (
                "recovery-search",
                "Recovery search",
                "system.catalog_search",
                "all_active",
            ),
        ):
            definition = CapabilityDefinition(
                slug=slug,
                kind="tool",
                name=name,
                description=name,
                category="test",
                icon="tool",
                status="published",
                source="creator",
                created_by=user.id,
                owner_id=user.id,
                visibility="platform",
                access_mode=access_mode,
                review_status="approved",
                created_at=now,
                updated_at=now,
            )
            session.add(definition)
            session.flush()
            version = CapabilityVersion(
                capability_id=definition.id,
                version=1,
                status="published",
                snapshot_json=CapabilitySnapshot(
                    kind="tool",
                    name=name,
                    description=name,
                    config={"tool": tool_name},
                    executionMode="simulated",
                ).model_dump_json(by_alias=True),
                created_by=user.id,
                published_by=user.id,
                created_at=now,
                published_at=now,
            )
            session.add(version)
            session.flush()
            session.add(
                CapabilityGrant(
                    capability_id=definition.id,
                    user_id=user.id,
                    granted_by=user.id,
                    created_at=now,
                )
            )
            tool_definitions.append((definition, version))
        agent_definition = CapabilityDefinition(
            slug="recovery-agent",
            kind="agent",
            name="Recovery agent",
            description="Recovery agent",
            category="test",
            icon="agent",
            status="published",
            source="creator",
            created_by=user.id,
            owner_id=user.id,
            visibility="platform",
            access_mode="all_active",
            review_status="approved",
            created_at=now,
            updated_at=now,
        )
        session.add(agent_definition)
        session.flush()
        agent_version = CapabilityVersion(
            capability_id=agent_definition.id,
            version=1,
            status="published",
            snapshot_json=CapabilitySnapshot(
                kind="agent",
                name=agent_definition.name,
                description=agent_definition.description,
                config={
                    "dependencies": [
                        {
                            "id": definition.id,
                            "versionId": version.id,
                            "kind": "tool",
                        }
                        for definition, version in tool_definitions
                    ]
                },
                executionMode="simulated",
            ).model_dump_json(by_alias=True),
            created_by=user.id,
            published_by=user.id,
            created_at=now,
            published_at=now,
        )
        session.add(agent_version)
        session.flush()
        session.add_all(
            [
                CapabilityDependency(
                    version_id=agent_version.id,
                    dependency_id=definition.id,
                    dependency_kind="tool",
                    dependency_version_id=version.id,
                )
                for definition, version in tool_definitions
            ]
        )
        run = AgentRun(
            user_id=user.id,
            conversation_id=conversation.id,
            assistant_message_id=assistant.id,
            client_turn_id="recovery-turn",
            idempotency_key=f"{user.id}:{conversation.id}:recovery-turn",
            capability_id=agent_definition.id,
            version_id=agent_version.id,
            mode="fake",
            provider="fake",
            status="waiting_tool",
            input_text=request.text,
            created_at=now,
            started_at=now,
            worker_id="dead-worker",
            heartbeat_at=now - timedelta(minutes=1),
            lease_expires_at=now - timedelta(seconds=1),
            deadline_at=now + timedelta(minutes=2),
            max_steps=6,
            max_tool_calls=6,
            input_token_budget=200_000,
            output_token_budget=100_000,
        )
        session.add(run)
        session.flush()
        first_tool_name = "tool_" + tool_definitions[0][0].id.replace("-", "_")
        second_tool_name = "tool_" + tool_definitions[1][0].id.replace("-", "_")
        session.add(
            RunMessage(
                run_id=run.id,
                seq=1,
                role="assistant",
                payload_json=json.dumps(
                    {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call-time-recovered",
                                "type": "function",
                                "function": {
                                    "name": first_tool_name,
                                    "arguments": "{}",
                                },
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                created_at=now,
            )
        )
        session.add(
            RunStep(
                run_id=run.id,
                seq=1,
                step_type="llm",
                name="fake",
                status="completed",
                input_json="{}",
                output_json=json.dumps(
                    {
                        "content": "",
                        "toolCalls": [
                            {
                                "id": "call-time-recovered",
                                "type": "function",
                                "function": {
                                    "name": first_tool_name,
                                    "arguments": "{}",
                                },
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                error="",
                started_at=now,
                finished_at=now,
                duration_ms=1,
            )
        )
        run.step_count = 1
        session.commit()
        return run.id, first_tool_name, second_tool_name


class RecoveryProvider:
    name = "recovery-provider"

    def __init__(self, first_tool_name: str, second_tool_name: str):
        self.first_tool_name = first_tool_name
        self.second_tool_name = second_tool_name
        self.messages = []

    async def stream(self, messages, *, tools=None):
        self.messages.append(json.loads(json.dumps(messages)))
        if len(self.messages) == 1:
            assert messages[-1]["role"] == "tool"
            assert messages[-1]["tool_call_id"] == "call-time-recovered"
            yield LLMChunk(
                tool_calls=[
                    {
                        "id": "call-search-recovered",
                        "type": "function",
                        "function": {
                            "name": self.second_tool_name,
                            "arguments": '{"query":"recovery"}',
                        },
                    }
                ],
                done=True,
                token_input=4,
                token_output=2,
            )
            return
        assert messages[-1]["role"] == "tool"
        assert messages[-1]["tool_call_id"] == "call-search-recovered"
        yield LLMChunk(text="recovered")
        yield LLMChunk(done=True, token_input=4, token_output=2)


def test_expired_run_resumes_pending_tool_without_duplicate_call_ids(monkeypatch):
    run_id, first_tool_name, second_tool_name = _seed_recoverable_run()
    provider = RecoveryProvider(first_tool_name, second_tool_name)
    monkeypatch.setattr(runtime_service_module, "build_provider", lambda: provider)

    async def recover_and_wait():
        recovered = await recover_expired_runs()
        assert recovered >= 1
        for _ in range(100):
            with SessionLocal() as session:
                run = session.get(AgentRun, run_id)
                if run is not None and run.status in {
                    "completed",
                    "failed",
                    "cancelled",
                    "timed_out",
                }:
                    return run.status
            await asyncio.sleep(0.02)
        with SessionLocal() as session:
            run = session.get(AgentRun, run_id)
            payloads = [
                json.loads(item.payload_json)
                for item in session.scalars(
                    select(RunMessage)
                    .where(RunMessage.run_id == run_id)
                    .order_by(RunMessage.seq)
                )
            ]
            raise AssertionError(
                (
                    "recovered run did not reach a terminal state",
                    run.status if run else None,
                    run.error_code if run else None,
                    run.error_message if run else None,
                    run.attempt if run else None,
                    run.worker_id if run else None,
                    run.tool_call_count if run else None,
                    payloads,
                )
            )

    assert asyncio.run(recover_and_wait()) == "completed"
    with SessionLocal() as session:
        run = session.get(AgentRun, run_id)
        messages = list(
            session.scalars(
                select(RunMessage)
                .where(RunMessage.run_id == run_id)
                .order_by(RunMessage.seq)
            )
        )
    assert run is not None
    assert run.attempt == 2
    payloads = [json.loads(message.payload_json) for message in messages]
    assert [item.get("tool_call_id") for item in payloads if item["role"] == "tool"] == [
        "call-time-recovered",
        "call-search-recovered",
    ]
    assert len(provider.messages) == 2


def test_resume_stream_reads_existing_terminal_run_without_new_run():
    run_id, _, _ = _seed_recoverable_run()
    with SessionLocal() as session:
        run = session.get(AgentRun, run_id)
        run.status = "completed"
        run.output_text = "existing result"
        run.lease_expires_at = None
        session.commit()

    async def collect():
        return [event async for event in _wait_for_background_run(run_id)]

    events = asyncio.run(collect())
    assert events == [
        {"type": "chunk", "content": "existing result"},
        {"type": "done", "runId": run_id, "status": "completed"},
    ]
    with SessionLocal() as session:
        assert len(list(session.scalars(select(AgentRun.id)))) == 1
