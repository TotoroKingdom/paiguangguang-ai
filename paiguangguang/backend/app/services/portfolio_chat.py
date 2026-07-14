from __future__ import annotations

from threading import Lock
from uuid import uuid4

from app.ai.deepseek import DeepSeekClient, DeepSeekError
from app.core.config import get_settings
from app.schemas.chat import ChatMessage, PortfolioChatData, PortfolioChatRequest

PORTFOLIO_FACTS = [
    "你是一个暖心的聊天的机器人",
]


def build_system_prompt() -> str:
    facts = "\n".join(f"- {fact}" for fact in PORTFOLIO_FACTS)
    return (
        "You are the portfolio assistant for Pai Guangguang's AI Engineer System.\n"
    )


class PortfolioChatMemory:
    def __init__(self) -> None:
        self._sessions: dict[str, list[ChatMessage]] = {}
        self._lock = Lock()

    def get_messages(self, session_id: str) -> list[ChatMessage]:
        with self._lock:
            return list(self._sessions.get(session_id, []))

    def append_turn(self, session_id: str, user_message: str, assistant_reply: str) -> None:
        with self._lock:
            history = self._sessions.setdefault(session_id, [])
            history.append(ChatMessage(role="user", content=user_message))
            history.append(ChatMessage(role="assistant", content=assistant_reply))

    def clear(self) -> None:
        with self._lock:
            self._sessions.clear()


class PortfolioChatService:
    def __init__(
        self,
        client: DeepSeekClient | None = None,
        memory: PortfolioChatMemory | None = None,
    ) -> None:
        self.client = client or DeepSeekClient(get_settings())
        self.memory = memory or PortfolioChatMemory()

    def reply(self, request: PortfolioChatRequest) -> PortfolioChatData:
        session_id = request.session_id or str(uuid4())
        messages = [{"role": "system", "content": build_system_prompt()}]
        messages.extend(message.model_dump() for message in self.memory.get_messages(session_id))
        messages.append({"role": "user", "content": request.message})

        result = self.client.chat_completions(messages)
        reply = self._extract_reply(result)
        self.memory.append_turn(session_id, request.message, reply)
        return PortfolioChatData(reply=reply, session_id=session_id)

    @staticmethod
    def _extract_reply(payload: dict[str, object]) -> str:
        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise DeepSeekError("DeepSeek returned no choices")

        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            raise DeepSeekError("DeepSeek returned an invalid choice payload")

        message = first_choice.get("message")
        if not isinstance(message, dict):
            raise DeepSeekError("DeepSeek returned an invalid message payload")

        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise DeepSeekError("DeepSeek returned an empty reply")

        return content.strip()


_PORTFOLIO_CHAT_SERVICE = PortfolioChatService()


def get_portfolio_chat_service() -> PortfolioChatService:
    return _PORTFOLIO_CHAT_SERVICE
