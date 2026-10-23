"""Learn Codex 05: fake model stream and turn-scoped client.

Python 3.10+. No network, API key, shell, or file writes.
Events and routing tokens are invented teaching data, NOT Codex protocol.
"""

from dataclasses import dataclass
from typing import Iterator


@dataclass(frozen=True)
class Prompt:
    input: tuple[str, ...]
    tools: tuple[str, ...] = ()


@dataclass(frozen=True)
class Event:
    kind: str
    value: str


class TemporaryTransportError(Exception):
    pass


class FakeProvider:
    """Yields deterministic event sequences as a streaming transport would."""

    def stream(
        self, turn_id: str, request: str, attempt: int, route_token: str | None
    ) -> Iterator[Event]:
        if request == "inspect" and attempt == 1:
            raise TemporaryTransportError("connection closed before first event")

        # A server may provide per-turn routing state. These labels are fake.
        if request == "inspect":
            assert route_token is None
            yield Event("created", f"resp-1|route:{turn_id}")
            yield Event("output_item_done", "tool:inspect_login")
            yield Event("completed", "end_turn=false")
        elif request == "answer":
            assert route_token == f"route:{turn_id}"
            yield Event("created", f"resp-2|route:{turn_id}")
            yield Event("output_text_delta", "模拟分析")
            yield Event("output_text_delta", "已完成")
            yield Event("output_item_done", "assistant_message")
            yield Event("completed", "end_turn=true")
        else:
            raise ValueError("unknown simulated request")


class ModelClient:
    """Holds provider-related settings shared by multiple turns."""

    def __init__(self) -> None:
        self.provider = FakeProvider()

    def new_session(self, turn_id: str) -> "ModelClientSession":
        return ModelClientSession(self.provider, turn_id)


class ModelClientSession:
    """Reused for model requests INSIDE one turn, never across turns."""

    def __init__(self, provider: FakeProvider, turn_id: str) -> None:
        self.provider = provider
        self.turn_id = turn_id
        self.route_token: str | None = None

    def sample(self, request: str, prompt: Prompt) -> list[Event]:
        if not prompt.input:
            raise ValueError("empty teaching prompt")

        for attempt in (1, 2):
            events: list[Event] = []
            try:
                print(f"request={request} attempt={attempt} route={self.route_token or '-'}")
                for event in self.provider.stream(
                    self.turn_id, request, attempt, self.route_token
                ):
                    events.append(event)
                    if event.kind == "created":
                        response_id, token = event.value.split("|", 1)
                        if self.route_token is None:
                            self.route_token = token
                        print(f"  {event.kind}: {response_id}")
                    else:
                        print(f"  {event.kind}: {event.value}")
                assert events[-1].kind == "completed"
                return events
            except TemporaryTransportError as exc:
                # Teaching simplification: only retry if NO events were emitted.
                if events or attempt == 2:
                    raise
                print(f"  retryable before output: {exc}")
        raise AssertionError("unreachable")


def main() -> None:
    client = ModelClient()
    turn = client.new_session("turn-1")
    first = turn.sample("inspect", Prompt(("检查登录模块",), ("inspect_login",)))
    assert any(e.value == "tool:inspect_login" for e in first)
    assert first[-1].value == "end_turn=false"

    # The Agent Runtime would execute a tool and append its observation.
    observation = "模拟工具返回：读取到登录模块"
    second = turn.sample(
        "answer", Prompt(("检查登录模块", observation), ("inspect_login",))
    )
    assert second[-1].value == "end_turn=true"
    assert "".join(e.value for e in second if e.kind == "output_text_delta") == "模拟分析已完成"
    assert turn.route_token == "route:turn-1"

    next_turn = client.new_session("turn-2")
    assert next_turn is not turn and next_turn.route_token is None
    print("next turn has fresh routing state")
    print("All teaching assertions passed")


if __name__ == "__main__":
    main()
