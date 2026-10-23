"""Chapter 06: deterministic context and prompt assembly (teaching model).

Python 3.10+. No API, network, filesystem scanning or project modification.
Not a Codex API implementation, tokenizer, security sandbox or prompt contract.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Item:
    role: str
    kind: str
    content: str


@dataclass(frozen=True)
class Prompt:
    base_instructions: str
    input: tuple[Item, ...]
    tools: tuple[str, ...]


class ContextManager:
    """Records original items; prepares a separate model-visible view."""

    def __init__(self) -> None:
        self._items: list[Item] = []

    def record(self, item: Item) -> None:
        self._items.append(item)

    def for_prompt(self, max_tool_chars: int = 88) -> tuple[Item, ...]:
        prepared: list[Item] = []
        for item in self._items:
            if item.kind == "tool_output" and len(item.content) > max_tool_chars:
                prepared.append(Item(item.role, item.kind,
                                     item.content[:max_tool_chars] + "…[teaching truncation]"))
            else:
                prepared.append(item)
        return tuple(prepared)

    @property
    def originals(self) -> tuple[Item, ...]:
        return tuple(self._items)


def build_prompt(history: ContextManager) -> Prompt:
    """Toy analogue of separating prepared input, base text, and tools."""
    return Prompt(
        base_instructions="你是代码分析助手。遵循有效权限，不要修改用户文件。",
        input=history.for_prompt(),
        tools=("read_file", "search_code"),
    )


def show(label: str, prompt: Prompt) -> None:
    print(label)
    print("  base:", prompt.base_instructions)
    print("  tools:", ", ".join(prompt.tools))
    for item in prompt.input:
        print(f"  [{item.role}/{item.kind}] {item.content}")


def main() -> None:
    history = ContextManager()
    # In real Codex these origins are more structured and policy dependent.
    history.record(Item("user", "project_instructions", "AGENTS.md（模拟）：只分析，不改代码"))
    history.record(Item("user", "task", "帮我检查登录模块"))
    first = build_prompt(history)
    show("First request", first)
    assert len(first.input) == 2

    history.record(Item("assistant", "tool_call", "read_file(call-1, login.py)"))
    long_output = "def login():\n" + "    # existing login logic\n" * 9
    history.record(Item("tool", "tool_output", long_output))
    second = build_prompt(history)
    show("Second request after tool observation", second)
    assert len(second.input) == 4
    assert second.input[-1].kind == "tool_output"
    assert "[teaching truncation]" in second.input[-1].content
    assert history.originals[-1].content == long_output
    assert len(second.input[-1].content) < len(long_output)
    assert first.input == history.originals[:2]
    print("Original history preserved; prompt snapshot normalized separately")
    print("All teaching assertions passed")


if __name__ == "__main__":
    main()
