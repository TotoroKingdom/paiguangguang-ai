import asyncio
import json
from types import SimpleNamespace

from sqlalchemy import select

from app.core.security import hash_user_password
from app.db import SessionLocal
from app.models import Conversation, Message
from app.modules.capabilities.schemas import CapabilitySnapshot
from app.modules.identity.models import User
from app.modules.identity.user_service import UserPrincipal
from app.modules.runtime import service as runtime_service_module
from app.modules.runtime.models import AgentRun, RunMessage, RunStep, RunTrace
from app.modules.runtime.providers import LLMChunk
from app.modules.runtime.service import RuntimeService
from app.repositories import OwnerScope, utc_now
from app.schemas import MessageRequest, TurnCreate


def _user_and_turn(session):
    now = utc_now()
    request_json = json.dumps(
        {
            "conversationId": None,
            "clientTurnId": "s2-loop-turn",
            "text": "请先查时间，再搜索天气",
            "capability": None,
            "fileIds": [],
            "simulateFailure": False,
        },
        ensure_ascii=False,
    )
    user = User(
        account_number="s2-loop-user",
        password_hash=hash_user_password("s2-loop-password"),
        nickname="S2 loop",
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
        title="S2 loop",
        created_at=now,
        updated_at=now,
        version=2,
    )
    user_message = Message(
        conversation=conversation,
        seq=1,
        client_turn_id="s2-loop-turn",
        role="user",
        content="请先查时间，再搜索天气",
        status="complete",
        steps_json="[]",
        capability_json="null",
        attachments_json="[]",
        request_json=request_json,
        created_at=now,
        updated_at=now,
    )
    assistant = Message(
        conversation=conversation,
        seq=2,
        role="assistant",
        content="",
        status="generating",
        steps_json="[]",
        capability_json="null",
        attachments_json="[]",
        request_json=request_json,
        created_at=now,
        updated_at=now,
    )
    conversation.messages.extend([user_message, assistant])
    session.add(conversation)
    session.flush()
    payload = TurnCreate(
        clientTurnId="s2-loop-turn",
        text=user_message.content,
        capability=None,
        attachments=[],
        request=MessageRequest(
            conversationId=conversation.id,
            clientTurnId="s2-loop-turn",
            text=user_message.content,
            fileIds=[],
        ),
    )
    principal = UserPrincipal(user=user, session=SimpleNamespace(scope="FULL"))
    return user, conversation, assistant, payload, principal


class ThreeRoundProvider:
    name = "deterministic-s2-provider"

    def __init__(self):
        self.requests: list[tuple[list[dict], list[dict] | None]] = []
        self.round = 0

    async def stream(self, messages, *, tools=None):
        self.requests.append((json.loads(json.dumps(messages)), json.loads(json.dumps(tools)) if tools is not None else None))
        self.round += 1
        if self.round == 1:
            tool = (tools or [])[0]["function"]
            name = tool["name"]
            arguments = '{"query":"天气"}' if "search" in tool.get("description", "").lower() else "{}"
            yield LLMChunk(
                tool_calls=[
                    {
                        "id": "call-time-1",
                        "type": "function",
                        "function": {
                            "name": name,
                            "arguments": arguments,
                        },
                    }
                ],
                done=True,
                token_input=10,
                token_output=5,
            )
        elif self.round == 2:
            tool = (tools or [])[1]["function"]
            name = tool["name"]
            arguments = '{"query":"天气"}' if "search" in tool.get("description", "").lower() else "{}"
            yield LLMChunk(
                tool_calls=[
                    {
                        "id": "call-search-1",
                        "type": "function",
                        "function": {
                            "name": name,
                            "arguments": arguments,
                        },
                    }
                ],
                done=True,
                token_input=10,
                token_output=5,
            )
        else:
            yield LLMChunk(text="最终答案：时间和天气已查询。")
            yield LLMChunk(done=True, token_input=10, token_output=5)


def _seed_published_agent_with_granted_tools(session, user):
    """Create the exact published/locked/granted records used by the loop."""

    from app.modules.capabilities.models import (
        CapabilityDefinition,
        CapabilityDependency,
        CapabilityGrant,
        CapabilityVersion,
    )

    now = utc_now()
    definitions = []
    for slug, kind, name, description, owner_id, access_mode in (
        (
            "s2-loop-time-tool",
            "tool",
            "S2 loop time",
            "Current time",
            "tool-owner-time",
            "granted",
        ),
        (
            "s2-loop-search-tool",
            "tool",
            "S2 loop search",
            "Catalog search",
            "tool-owner-search",
            "granted",
        ),
        (
            "s2-loop-agent",
            "agent",
            "S2 loop agent",
            "Deterministic Agent",
            user.id,
            "all_active",
        ),
    ):
        definition = CapabilityDefinition(
            slug=slug,
            kind=kind,
            name=name,
            description=description,
            category="test",
            icon="tool" if kind == "tool" else "agent",
            status="published",
            source="creator",
            created_by=user.id,
            owner_id=owner_id,
            visibility="platform",
            access_mode=access_mode,
            review_status="approved",
            created_at=now,
            updated_at=now,
        )
        definitions.append(definition)
    session.add_all(definitions)
    session.flush()
    time_definition, search_definition, agent_definition = definitions

    tool_versions = []
    for definition, tool_name in (
        (time_definition, "system.current_time"),
        (search_definition, "system.catalog_search"),
    ):
        version = CapabilityVersion(
            capability_id=definition.id,
            version=1,
            status="published",
            snapshot_json=json.dumps(
                CapabilitySnapshot(
                    kind="tool",
                    name=definition.name,
                    description=definition.description,
                    config={"tool": tool_name},
                    executionMode="simulated",
                ).model_dump(by_alias=True),
                ensure_ascii=False,
            ),
            created_by=user.id,
            published_by=user.id,
            created_at=now,
            published_at=now,
        )
        tool_versions.append(version)
    agent_version = CapabilityVersion(
        capability_id=agent_definition.id,
        version=1,
        status="published",
        snapshot_json=json.dumps(
            CapabilitySnapshot(
                kind="agent",
                name=agent_definition.name,
                description=agent_definition.description,
                config={
                    "dependencies": [
                        {"id": time_definition.id, "versionId": "pending", "kind": "tool"},
                        {"id": search_definition.id, "versionId": "pending", "kind": "tool"},
                    ]
                },
                executionMode="simulated",
            ).model_dump(by_alias=True),
            ensure_ascii=False,
        ),
        created_by=user.id,
        published_by=user.id,
        created_at=now,
        published_at=now,
    )
    session.add_all([*tool_versions, agent_version])
    session.flush()
    agent_version.snapshot_json = json.dumps(
        CapabilitySnapshot(
            kind="agent",
            name=agent_definition.name,
            description=agent_definition.description,
            config={
                "dependencies": [
                    {"id": time_definition.id, "versionId": tool_versions[0].id, "kind": "tool"},
                    {"id": search_definition.id, "versionId": tool_versions[1].id, "kind": "tool"},
                ]
            },
            executionMode="simulated",
        ).model_dump(by_alias=True),
        ensure_ascii=False,
    )
    session.add_all(
        [
            CapabilityDependency(
                version_id=agent_version.id,
                dependency_id=time_definition.id,
                dependency_kind="tool",
                dependency_version_id=tool_versions[0].id,
            ),
            CapabilityDependency(
                version_id=agent_version.id,
                dependency_id=search_definition.id,
                dependency_kind="tool",
                dependency_version_id=tool_versions[1].id,
            ),
            CapabilityGrant(
                capability_id=time_definition.id,
                user_id=user.id,
                granted_by=user.id,
                created_at=now,
            ),
            CapabilityGrant(
                capability_id=search_definition.id,
                user_id=user.id,
                granted_by=user.id,
                created_at=now,
            ),
        ]
    )
    session.flush()
    return agent_definition, agent_version


def test_agent_loop_runs_two_tools_then_final_answer_and_persists_protocol(monkeypatch):
    """A deterministic three-round model proves tool-call/message ordering."""

    with SessionLocal() as session:
        user, conversation, assistant, payload, principal = _user_and_turn(session)
        agent_definition, agent_version = _seed_published_agent_with_granted_tools(session, user)
        session.commit()
        run_service = RuntimeService(session)
        run = run_service.create_run(
            principal,
            conversation_id=conversation.id,
            version_id=agent_version.id,
            capability_id=agent_definition.id,
            input_text=payload.text,
        )

        provider = ThreeRoundProvider()
        monkeypatch.setattr(runtime_service_module, "build_provider", lambda: provider)

        events = []

        async def collect():
            async for event in run_service.stream(
                run,
                principal=principal,
                scope=OwnerScope(owner_id="", user_id=principal.user.id),
                assistant_message_id=assistant.id,
                payload=payload,
            ):
                events.append(event)

        asyncio.run(collect())
        session.expire_all()
        stored_run = session.get(AgentRun, run.id)
        stored_assistant = session.get(Message, assistant.id)
        protocol_messages = list(
            session.scalars(
                select(RunMessage)
                .where(RunMessage.run_id == run.id)
                .order_by(RunMessage.seq)
            )
        )
        steps = list(session.scalars(select(RunStep).where(RunStep.run_id == run.id).order_by(RunStep.seq)))
        traces = list(session.scalars(select(RunTrace).where(RunTrace.run_id == run.id).order_by(RunTrace.seq)))

    assert stored_run is not None
    assert stored_run.status == "completed", (stored_run.error_code, stored_run.error_message)
    assert stored_run.output_text == "最终答案：时间和天气已查询。"
    assert stored_assistant is not None
    assert stored_assistant.status == "complete"
    assert stored_assistant.content == stored_run.output_text
    assert [message.role for message in protocol_messages] == [
        "assistant",
        "tool",
        "assistant",
        "tool",
        "assistant",
    ]
    protocol_payloads = [json.loads(message.payload_json) for message in protocol_messages]
    first_tool_name = provider.requests[0][1][0]["function"]["name"]
    second_tool_name = provider.requests[0][1][1]["function"]["name"]
    assert protocol_payloads[0]["tool_calls"][0]["id"] == "call-time-1"
    assert protocol_payloads[0]["tool_calls"][0]["function"]["name"] == first_tool_name
    assert protocol_payloads[1]["tool_call_id"] == "call-time-1"
    assert protocol_payloads[2]["tool_calls"][0]["id"] == "call-search-1"
    assert protocol_payloads[2]["tool_calls"][0]["function"]["name"] == second_tool_name
    assert protocol_payloads[3]["tool_call_id"] == "call-search-1"
    assert protocol_payloads[4] == {
        "role": "assistant",
        "content": "最终答案：时间和天气已查询。",
    }
    assert [event["type"] for event in events if event["type"] in {"tool", "done"}] == [
        "tool",
        "tool",
        "done",
    ]

    assert len(provider.requests) == 3
    assert provider.requests[0][1] and provider.requests[0][1][0]["function"]["name"] == first_tool_name
    assert provider.requests[1][1] and provider.requests[1][1][0]["function"]["name"] == first_tool_name
    assert provider.requests[2][1] and provider.requests[2][1][1]["function"]["name"] == second_tool_name
    assert provider.requests[1][0][-2]["role"] == "assistant"
    assert provider.requests[1][0][-2]["tool_calls"][0]["id"] == "call-time-1"
    assert provider.requests[1][0][-1]["role"] == "tool"
    assert provider.requests[1][0][-1]["tool_call_id"] == "call-time-1"
    assert provider.requests[2][0][-2]["tool_calls"][0]["id"] == "call-search-1"
    assert provider.requests[2][0][-1]["tool_call_id"] == "call-search-1"

    assistant_call_steps = [step for step in steps if step.step_type == "llm" and json.loads(step.output_json).get("toolCalls")]
    assert [json.loads(step.output_json)["toolCalls"][0]["id"] for step in assistant_call_steps] == [
        "call-time-1",
        "call-search-1",
    ]
    tool_steps = [step for step in steps if step.step_type == "tool"]
    assert [json.loads(step.input_json)["toolCallId"] for step in tool_steps] == [
        "call-time-1",
        "call-search-1",
    ]
    assert [json.loads(trace.detail_json).get("toolCallId") for trace in traces if trace.event == "tool.completed"] == [
        "call-time-1",
        "call-search-1",
    ]


def test_locked_agent_tool_is_rejected_without_real_user_grant():
    """The locked dependency still passes the live ACL check at execution time."""

    from app.core.errors import APIError
    from app.modules.capabilities.models import (
        CapabilityDefinition,
        CapabilityDependency,
        CapabilityVersion,
    )

    with SessionLocal() as session:
        user, _, _, _, principal = _user_and_turn(session)
        now = utc_now()
        tool_definition = CapabilityDefinition(
            slug="s2-acl-tool",
            kind="tool",
            name="S2 ACL tool",
            description="read-only test tool",
            category="test",
            icon="tool",
            status="published",
            source="creator",
            created_by=user.id,
            owner_id="different-owner",
            visibility="platform",
            access_mode="granted",
            review_status="approved",
            created_at=now,
            updated_at=now,
        )
        agent_definition = CapabilityDefinition(
            slug="s2-acl-agent",
            kind="agent",
            name="S2 ACL agent",
            description="agent with a locked tool",
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
        session.add_all([tool_definition, agent_definition])
        session.flush()
        tool_version = CapabilityVersion(
            capability_id=tool_definition.id,
            version=1,
            status="published",
            snapshot_json=json.dumps(
                CapabilitySnapshot(
                    kind="tool",
                    name="S2 ACL tool",
                    config={"tool": "system.current_time"},
                    executionMode="simulated",
                ).model_dump(by_alias=True),
                ensure_ascii=False,
            ),
            created_by=user.id,
            published_by=user.id,
            created_at=now,
            published_at=now,
        )
        agent_version = CapabilityVersion(
            capability_id=agent_definition.id,
            version=1,
            status="published",
            snapshot_json=json.dumps(
                CapabilitySnapshot(
                    kind="agent",
                    name="S2 ACL agent",
                    config={},
                    executionMode="simulated",
                ).model_dump(by_alias=True),
                ensure_ascii=False,
            ),
            created_by=user.id,
            published_by=user.id,
            created_at=now,
            published_at=now,
        )
        session.add_all([tool_version, agent_version])
        session.flush()
        session.add(
            CapabilityDependency(
                version_id=agent_version.id,
                dependency_id=tool_definition.id,
                dependency_kind="tool",
                dependency_version_id=tool_version.id,
            )
        )
        run = AgentRun(
            user_id=user.id,
            capability_id=agent_definition.id,
            version_id=agent_version.id,
            mode="fake",
            provider="fake",
            status="running",
            input_text="acl test",
            created_at=now,
            started_at=now,
        )
        session.add(run)
        session.commit()

        try:
            RuntimeService(session)._agent_tools(run, principal)
        except APIError as error:
            assert error.code == "AGENT_DEPENDENCY_REVOKED"
        else:
            raise AssertionError("ungranted locked tool must be rejected by live ACL")

