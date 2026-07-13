from __future__ import annotations

from app.chatbot.llm.prompt_builder import PromptBuilder


def test_prompt_builder_builds_request_with_prompt_version_and_messages() -> None:
    builder = PromptBuilder(
        prompt_version="chatbot-v1",
        system_prompt="You are a chatbot.",
    )

    request = builder.build_request(
        request_id="req-1",
        model="deepseek-chat",
        user_message="Hello",
        history=(
            {"role": "assistant", "content": "Hi there"},
        ),
        temperature=0.2,
    )

    assert request.prompt_version == "chatbot-v1"
    assert request.request_id == "req-1"
    assert request.model == "deepseek-chat"
    assert request.temperature == 0.2
    assert [message.role for message in request.messages] == ["system", "assistant", "user"]
    assert request.messages[0].content == "You are a chatbot."
    assert request.messages[-1].content == "Hello"
    assert not hasattr(request, "raw_prompt")
