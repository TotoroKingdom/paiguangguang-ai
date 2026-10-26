"""Chapter 12 teaching model: Token Budget and Compaction.

Python 3.10+; no dependencies, network, LLM calls, or project-file changes.
Figures are *illustrative token units*, not a real tokenizer.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Budget:
    hard_limit: int
    auto_limit: int
    fallback_buffer: int = 0
    prefill: int = 0
    scope: str = "total"  # total or body_after_prefix
    post_turn_percent: int = 0


@dataclass(frozen=True)
class Status:
    active: int
    scope_used: int
    scope_limit: int
    remaining_base: int
    token_limit_reached: bool
    post_turn_due: bool


def status(used: int, budget: Budget) -> Status:
    assert used >= 0 and budget.hard_limit > 0 and budget.auto_limit > 0
    assert budget.scope in ("total", "body_after_prefix")
    scope_used = used if budget.scope == "total" else max(0, used - budget.prefill)
    base_remaining = min(max(0, budget.auto_limit - scope_used),
                         max(0, budget.hard_limit - used))
    due = scope_used >= budget.auto_limit + budget.fallback_buffer or used >= budget.hard_limit
    post_due = budget.post_turn_percent > 0 and (
        due or used * 100 >= budget.hard_limit * budget.post_turn_percent
    )
    return Status(used, scope_used, budget.auto_limit, base_remaining, due, post_due)


@dataclass(frozen=True)
class Item:
    kind: str
    text: str


@dataclass(frozen=True)
class BackgroundCandidate:
    history_version: int
    summary: str


class ToyContext:
    def __init__(self, items: list[Item]):
        self.items = list(items)
        self.version = 0
        self.rollout: list[tuple[str, tuple[Item, ...]]] = []

    def append(self, item: Item) -> None:
        self.items.append(item)
        self.version += 1

    def capture_candidate(self, summary: str) -> BackgroundCandidate:
        # A real V2 candidate additionally checks model/hash/auth generation.
        return BackgroundCandidate(self.version, summary)

    def install(self, candidate: BackgroundCandidate) -> bool:
        if candidate.history_version != self.version:
            return False  # Stale async output must not replace changed history.
        previous = tuple(self.items)
        recent_user = [x for x in self.items if x.kind == "user"][-1:]
        # Simplified local-summary shape; preserves current instruction + a user
        # message + a prewritten summary. No real summarization takes place.
        instructions = [x for x in self.items if x.kind == "instructions"][-1:]
        self.items = instructions + recent_user + [Item("summary", candidate.summary)]
        self.version += 1
        self.rollout.append(("compacted", previous))
        return True

    def reset_window(self) -> None:
        # Toy analogy to the TokenBudget feature's fresh-window path.
        previous = tuple(self.items)
        instructions = [x for x in self.items if x.kind == "instructions"][-1:]
        self.items = instructions + [Item("new_window", "new context begins")]
        self.version += 1
        self.rollout.append(("window_reset", previous))


def main() -> None:
    total = Budget(hard_limit=100, auto_limit=70, fallback_buffer=5)
    assert not status(74, total).token_limit_reached
    assert status(75, total).token_limit_reached
    assert status(100, total).token_limit_reached
    print("total-scope: 74 -> not due; 75 -> due; 100 -> hard limit")

    body = Budget(hard_limit=100, auto_limit=70, fallback_buffer=5,
                  prefill=50, scope="body_after_prefix")
    assert not status(78, body).token_limit_reached  # 28 body tokens
    assert status(100, body).token_limit_reached  # hard cap still wins
    print("body-after-prefix: active=78, body=28 -> not due; hard cap=100 -> due")

    post = Budget(hard_limit=100, auto_limit=95, post_turn_percent=80)
    assert not status(82, post).token_limit_reached
    assert status(82, post).post_turn_due
    print("post-turn: 82% -> due, even without normal token-limit trigger")

    context = ToyContext([
        Item("instructions", "Project rules: no writes"),
        Item("user", "Analyze login failure"),
        Item("tool", "test stdout: failed 1"),
        Item("assistant", "I need to check the assertion"),
    ])
    old_candidate = context.capture_candidate("OLD summary")
    context.append(Item("user", "Do not change code"))
    assert not context.install(old_candidate)
    assert len(context.items) == 5
    assert not context.rollout
    print("stale background compaction rejected (history version changed)")

    candidate = context.capture_candidate("The login assertion failed; do not edit")
    assert context.install(candidate)
    assert [x.kind for x in context.items] == ["instructions", "user", "summary"]
    assert len(context.rollout[0][1]) == 5
    assert context.items[-2].text == "Do not change code"
    print("summary compaction installed; original events retained in toy rollout")

    context.reset_window()
    assert [x.kind for x in context.items] == ["instructions", "new_window"]
    assert context.rollout[-1][0] == "window_reset"
    print("TokenBudget-style fresh window: no model summary requested")
    print("All teaching assertions passed")


if __name__ == "__main__":
    main()
