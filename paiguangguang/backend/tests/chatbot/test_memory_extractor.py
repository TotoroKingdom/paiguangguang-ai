from __future__ import annotations

from dataclasses import dataclass, field

from app.chatbot.llm.provider import ChatCompletionRequest, ChatCompletionResult, ChatCompletionUsage, LLMMessage
from app.chatbot.memory.memory_extractor import MemoryExtractor
from app.core.config import Settings


@dataclass
class FakeLLMClient:
    outcomes: list[ChatCompletionResult] = field(default_factory=list)
    complete_calls: list[ChatCompletionRequest] = field(default_factory=list)

    def complete(self, request: ChatCompletionRequest) -> ChatCompletionResult:
        self.complete_calls.append(request)
        if not self.outcomes:
            raise AssertionError("Unexpected LLM call")
        return self.outcomes.pop(0)

    def close(self) -> None:
        return None


def _build_extractor(llm_client: FakeLLMClient | None = None) -> MemoryExtractor:
    return MemoryExtractor(
        llm_client=llm_client,
        settings=Settings(
            chatbot_default_model="deepseek-chat",
            chatbot_memory_min_confidence=0.75,
            chatbot_long_term_memory_enabled=True,
        ),
    )


def test_memory_extractor_detects_direct_remember_and_rejects_sensitive_content() -> None:
    extractor = _build_extractor()
    source_message_ids = [
        "00000000-0000-0000-0000-000000000101",
        "00000000-0000-0000-0000-000000000102",
    ]

    drafts = extractor.extract(
        user_message="请记住我的项目名是星轨",
        assistant_message="好的，我记住了。",
        user_id="user-1",
        conversation_id="conversation-1",
        source_message_ids=source_message_ids,
    )

    assert len(drafts) == 1
    draft = drafts[0]
    assert draft.source == "rule"
    assert draft.action == "upsert"
    assert draft.memory_type == "project_context"
    assert draft.content == "项目名是星轨"
    assert draft.status == "active"
    assert draft.confidence >= 0.9
    assert draft.importance >= 0.6
    assert draft.source_message_ids == tuple(source_message_ids)

    rejected = extractor.extract(
        user_message="请记住我的密码是secret-123",
        assistant_message="我会帮你记录。",
        user_id="user-1",
        conversation_id="conversation-1",
        source_message_ids=source_message_ids,
    )

    assert rejected == []


def test_memory_extractor_uses_llm_fallback_for_implicit_candidate() -> None:
    fake_llm = FakeLLMClient(
        outcomes=[
            ChatCompletionResult(
                request_id="00000000-0000-0000-0000-000000000201",
                prompt_version="memory-v1",
                model="deepseek-chat",
                message=LLMMessage(
                    role="assistant",
                    content=(
                        '[{"action":"upsert","memory_type":"preference","content":"我喜欢深色主题",'
                        '"confidence":0.82,"importance":0.55,"status":"active"}]'
                    ),
                ),
                finish_reason="stop",
                usage=ChatCompletionUsage(prompt_tokens=13, completion_tokens=27, total_tokens=40),
            )
        ]
    )
    extractor = _build_extractor(fake_llm)

    drafts = extractor.extract(
        user_message="这条偏好要保留：界面尽量保持深色主题",
        assistant_message="明白。",
        user_id="user-1",
        conversation_id="conversation-1",
        source_message_ids=["00000000-0000-0000-0000-000000000301"],
    )

    assert len(fake_llm.complete_calls) == 1
    assert len(drafts) == 1
    draft = drafts[0]
    assert draft.source == "llm"
    assert draft.action == "upsert"
    assert draft.memory_type == "preference"
    assert draft.content == "我喜欢深色主题"
    assert draft.confidence == 0.82
    assert draft.importance == 0.55
