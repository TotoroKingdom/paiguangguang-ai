from __future__ import annotations

from dataclasses import dataclass
from math import ceil

from app.chatbot.llm.provider import LLMMessage


@dataclass(frozen=True, slots=True)
class ApproxTokenEstimator:
    chars_per_token: int = 4
    message_overhead: int = 4
    section_overhead: int = 6

    def estimate_text(self, text: str) -> int:
        normalized = " ".join(text.split())
        if not normalized:
            return 0
        return max(1, ceil(len(normalized) / max(1, self.chars_per_token)))

    def estimate_message(self, message: LLMMessage | str) -> int:
        content = message.content if isinstance(message, LLMMessage) else str(message)
        return self.message_overhead + self.estimate_text(content)

    def estimate_section(self, content: str, *, source_count: int = 0) -> int:
        return self.section_overhead + self.estimate_text(content) + max(0, source_count)
