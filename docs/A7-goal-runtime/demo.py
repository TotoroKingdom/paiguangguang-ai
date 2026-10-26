"""A7: offline teaching model of persisted, thread-scoped Codex Goal Runtime.

Python 3.10+ standard library only. No model, threads, shell, network,
real Codex state DB or scheduler. Not a replica of production persistence.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from enum import Enum
import json
from pathlib import Path
from tempfile import TemporaryDirectory


class Status(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    BLOCKED = "blocked"
    BUDGET_LIMITED = "budget_limited"
    USAGE_LIMITED = "usage_limited"
    COMPLETE = "complete"


@dataclass
class Goal:
    thread_id: str
    goal_id: str
    objective: str
    status: Status = Status.ACTIVE
    token_budget: int | None = None
    tokens_used: int = 0
    time_used_seconds: int = 0
    blocker: str | None = None
    blocker_streak: int = 0


class GoalStore:
    """Tiny JSON persistence under a temporary directory."""

    def __init__(self, root: Path):
        self.root = root

    def load(self, thread_id: str) -> Goal | None:
        file = self.root / f"{thread_id}.json"
        if not file.exists():
            return None
        raw = json.loads(file.read_text(encoding="utf-8"))
        raw["status"] = Status(raw["status"])
        return Goal(**raw)

    def put(self, goal: Goal) -> None:
        self.root.joinpath(f"{goal.thread_id}.json").write_text(
            json.dumps(asdict(goal), ensure_ascii=False), encoding="utf-8"
        )

    def create(self, thread: str, objective: str, budget: int | None = None) -> Goal:
        if not objective.strip():
            raise ValueError("objective required")
        if budget is not None and budget <= 0:
            raise ValueError("positive token budget required")
        previous = self.load(thread)
        if previous is not None and previous.status is not Status.COMPLETE:
            raise ValueError("cannot overwrite unfinished goal")
        goal = Goal(thread, f"{thread}-goal", objective, token_budget=budget)
        self.put(goal)
        return goal


class GoalRuntime:
    def __init__(self, store: GoalStore, thread: str):
        self.store, self.thread = store, thread
        self.live = True
        self.turn_running = False
        self.continuations = 0

    def resume_from_store(self) -> Goal | None:
        return self.store.load(self.thread)

    def continue_if_idle(self) -> bool:
        """Imitates host admission, not automatic background scheduling."""
        goal = self.store.load(self.thread)
        if not self.live or self.turn_running or goal is None:
            return False
        if goal.status is not Status.ACTIVE:
            return False
        self.turn_running = True
        self.continuations += 1
        return True

    def finish_turn(self, *, tokens: int, seconds: int, verified_complete: bool = False,
                    blocker: str | None = None, empty: bool = False) -> Goal:
        if not self.turn_running:
            raise RuntimeError("no running goal turn")
        goal = self.store.load(self.thread)
        assert goal is not None
        self.turn_running = False
        goal.tokens_used += tokens
        goal.time_used_seconds += seconds
        if goal.token_budget is not None and goal.tokens_used >= goal.token_budget:
            # Budget limitation is not achievement.
            goal.status = Status.BUDGET_LIMITED
        elif verified_complete:
            goal.status = Status.COMPLETE
        elif blocker is not None:
            goal.blocker_streak = goal.blocker_streak + 1 if goal.blocker == blocker else 1
            goal.blocker = blocker
            if goal.blocker_streak >= 3:
                goal.status = Status.BLOCKED
        elif not empty:
            goal.blocker_streak = 0
            goal.blocker = None
        self.store.put(goal)
        return goal

    def user_pause(self, *, explicitly_requested: bool) -> Goal:
        if not explicitly_requested:
            raise PermissionError("agent must not invent a pause request")
        goal = self.store.load(self.thread)
        assert goal is not None
        if goal.status is Status.BUDGET_LIMITED:
            return goal  # Budget limit takes precedence.
        goal.status = Status.PAUSED
        self.store.put(goal)
        return goal

    def user_resume(self) -> Goal:
        goal = self.store.load(self.thread)
        assert goal is not None
        if goal.status not in (Status.PAUSED, Status.BLOCKED):
            raise ValueError("not user-resumable in this teaching example")
        goal.status = Status.ACTIVE
        goal.blocker = None
        goal.blocker_streak = 0
        self.store.put(goal)
        return goal


def test_demo() -> None:
    with TemporaryDirectory() as directory:
        store = GoalStore(Path(directory))
        goal = store.create("thread-1", "完成三个接口的真实验收", budget=300)
        assert goal.status is Status.ACTIVE
        try:
            store.create("thread-1", "偷偷替换目标")
            raise AssertionError("unfinished goal overwritten")
        except ValueError:
            pass
        print("1. explicit goal persisted; unfinished goal cannot be overwritten")

        runtime = GoalRuntime(store, "thread-1")
        assert runtime.continue_if_idle() and not runtime.continue_if_idle()
        step = runtime.finish_turn(tokens=110, seconds=12, blocker="upstream-403")
        assert step.status is Status.ACTIVE and step.blocker_streak == 1
        assert runtime.continue_if_idle()
        step = runtime.finish_turn(tokens=90, seconds=9, blocker="upstream-403")
        assert step.status is Status.ACTIVE and step.blocker_streak == 2
        print("2. idle admission is conditional; two blockers do not complete goal")

        assert runtime.continue_if_idle()
        step = runtime.finish_turn(tokens=20, seconds=4, blocker="upstream-403")
        assert step.status is Status.BLOCKED and not runtime.continue_if_idle()
        print("3. three consecutive same blockers -> blocked, not infinite retries")

        runtime.user_resume()
        assert runtime.continue_if_idle()
        step = runtime.finish_turn(tokens=80, seconds=6, verified_complete=False)
        assert step.status is Status.BUDGET_LIMITED and step.tokens_used == 300
        assert not runtime.continue_if_idle()
        assert runtime.user_pause(explicitly_requested=True).status is Status.BUDGET_LIMITED
        print("4. budget exhausted -> budget_limited; never fake complete")

        another = store.create("thread-2", "核对审计报告")
        assert another.thread_id == "thread-2"
        rt2 = GoalRuntime(store, "thread-2")
        try:
            rt2.user_pause(explicitly_requested=False)
            raise AssertionError("invented pause succeeded")
        except PermissionError:
            pass
        assert rt2.user_pause(explicitly_requested=True).status is Status.PAUSED
        assert not rt2.continue_if_idle()
        assert rt2.user_resume().status is Status.ACTIVE
        print("5. pause requires explicit user request; resume resets blocking audit")

        rt2.live = False
        assert not rt2.continue_if_idle()
        restored = GoalRuntime(store, "thread-2")
        assert restored.resume_from_store().objective == "核对审计报告"
        assert restored.continue_if_idle()
        step = restored.finish_turn(tokens=12, seconds=2, verified_complete=True)
        assert step.status is Status.COMPLETE
        assert not restored.continue_if_idle()
        print("6. persisted state survives runtime recreation; no offline scheduler implied")
        print("All teaching assertions passed")


if __name__ == "__main__":
    test_demo()
