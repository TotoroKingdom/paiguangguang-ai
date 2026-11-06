"""Chapter 07: a miniature Tool Spec / Registry / Router / Handler.

Python 3.10+, standard library only. All files and results are in memory.
This is a teaching model, NOT actual Codex tools, policy, or sandbox.
"""
from dataclasses import dataclass
import json
from typing import Protocol


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    required_arg: str


@dataclass(frozen=True)
class ToolCall:
    call_id: str
    name: str
    arguments_json: str


@dataclass(frozen=True)
class ToolResult:
    call_id: str
    ok: bool
    output: str


class Handler(Protocol):
    spec: ToolSpec

    def execute(self, argument: str) -> str: ...


class ReadFileHandler:
    spec = ToolSpec("read_file", "Read a sample project file", "path")
    _files = {"src/login.py": "def login(): return check_password()"}

    def execute(self, argument: str) -> str:
        if argument not in self._files:
            raise ValueError("path not found in teaching data")
        return self._files[argument]


class RunTestsHandler:
    spec = ToolSpec("run_tests", "Get predefined test results", "suite")

    def execute(self, argument: str) -> str:
        if argument != "login":
            raise ValueError("unknown test suite")
        return "login tests: 1 failure (simulated)"


class InternalNoteHandler:
    spec = ToolSpec("internal_note", "Internal-only demonstration tool", "text")

    def execute(self, argument: str) -> str:
        return f"internal: {argument}"


class ToolRegistry:
    def __init__(self) -> None:
        self._handlers: dict[str, Handler] = {}
        self._model_visible: set[str] = set()

    def register(self, handler: Handler, *, model_visible: bool) -> None:
        name = handler.spec.name
        if name in self._handlers:
            raise ValueError(f"duplicate tool: {name}")
        self._handlers[name] = handler
        if model_visible:
            self._model_visible.add(name)

    def model_specs(self) -> tuple[ToolSpec, ...]:
        return tuple(h.spec for name, h in self._handlers.items()
                     if name in self._model_visible)

    def resolve_model_call(self, name: str) -> Handler:
        if name not in self._model_visible:
            raise ValueError("tool not available to this model request")
        return self._handlers[name]


class ToolRouter:
    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry

    def dispatch(self, call: ToolCall) -> ToolResult:
        try:
            handler = self.registry.resolve_model_call(call.name)
            args = json.loads(call.arguments_json)
            if not isinstance(args, dict):
                raise ValueError("arguments must be a JSON object")
            expected = handler.spec.required_arg
            if set(args) != {expected} or not isinstance(args[expected], str):
                raise ValueError(f"expected string argument: {expected}")
            output = handler.execute(args[expected])
            return ToolResult(call.call_id, True, output)
        except (ValueError, KeyError, json.JSONDecodeError) as exc:
            return ToolResult(call.call_id, False, f"tool error: {exc}")


def main() -> None:
    registry = ToolRegistry()
    registry.register(ReadFileHandler(), model_visible=True)
    registry.register(RunTestsHandler(), model_visible=True)
    registry.register(InternalNoteHandler(), model_visible=False)
    router = ToolRouter(registry)

    print("advertised:", [s.name for s in registry.model_specs()])
    assert [s.name for s in registry.model_specs()] == ["read_file", "run_tests"]

    calls = [
        ToolCall("c1", "read_file", '{"path":"src/login.py"}'),
        ToolCall("c2", "run_tests", '{"suite":"login"}'),
        ToolCall("c3", "internal_note", '{"text":"secret"}'),
        ToolCall("c4", "missing_tool", '{}'),
        ToolCall("c5", "read_file", '{"path":42}'),
    ]
    results = [router.dispatch(call) for call in calls]
    for result in results:
        print(f"{result.call_id}: ok={result.ok}; {result.output}")

    assert [r.ok for r in results] == [True, True, False, False, False]
    assert [r.call_id for r in results] == [c.call_id for c in calls]
    print("next model request can use the two successful tool observations")
    print("All teaching assertions passed")


if __name__ == "__main__":
    main()
