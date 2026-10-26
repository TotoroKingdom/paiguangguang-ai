"""A5 Memory: offline Phase 1/Phase 2, leases, index and evidence-aware read.

Python 3.10+, standard library only; no model, network, SQL, credentials or
existing Codex memory files. This is a teaching simulation, NOT Codex's protocol.
"""
from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class Rollout:
    thread_id: str
    updated_day: int
    idle_hours: int
    source: str
    lines: tuple[str, ...]


@dataclass(frozen=True)
class Stage1:
    thread_id: str
    generated_day: int
    rollout_summary: str
    rollout_slug: str
    raw_memory: str | None  # V2 does not produce raw_memory.
    last_usage_day: int | None = None
    usage_count: int = 0


class ToyMemoryStore:
    def __init__(self, *, max_age_days: int = 30, min_idle_hours: int = 2) -> None:
        self.max_age_days = max_age_days
        self.min_idle_hours = min_idle_hours
        self.jobs: dict[str, str] = {}
        self.stage1: dict[str, Stage1] = {}
        self.phase2_owner: str | None = None
        self.summary = ""
        self.index: dict[str, str] = {}
        self.watermark = 0

    def claim(self, rollout: Rollout, *, now_day: int, owner: str) -> bool:
        if rollout.source != "interactive":
            return False
        if not 0 <= now_day - rollout.updated_day <= self.max_age_days:
            return False
        if rollout.idle_hours < self.min_idle_hours:
            return False
        if rollout.thread_id in self.stage1 or rollout.thread_id in self.jobs:
            return False
        self.jobs[rollout.thread_id] = owner
        return True

    def extract(self, rollout: Rollout, *, owner: str, version: str, now_day: int) -> Stage1:
        if self.jobs.get(rollout.thread_id) != owner:
            raise PermissionError("missing Phase 1 claim")
        if version not in {"v1", "v2"}:
            raise ValueError("unsupported memory version")
        # Only curated evidence; real Codex uses a MODEL with a strict schema.
        useful = [line for line in rollout.lines if line.startswith(("USER:", "RESULT:"))]
        safe = [re.sub(r"(?i)(token|password)=[^\s]+", r"\1=[REDACTED]", x)
                for x in useful]
        summary = " | ".join(safe)
        stage = Stage1(rollout.thread_id, now_day, summary,
                       "task-" + rollout.thread_id, summary if version == "v1" else None)
        self.stage1[rollout.thread_id] = stage
        del self.jobs[rollout.thread_id]
        return stage

    def acquire_phase2(self, owner: str) -> bool:
        if self.phase2_owner is not None:
            return False
        self.phase2_owner = owner
        return True

    def consolidate(self, *, owner: str, version: str, now_day: int,
                    max_unused_days: int = 60, limit: int = 5) -> None:
        if self.phase2_owner != owner:
            raise PermissionError("Phase 2 global lease required")
        try:
            candidates = [m for m in self.stage1.values()
                          if now_day - (m.last_usage_day if m.last_usage_day is not None
                                        else m.generated_day) <= max_unused_days]
            # Ranking for selection, stable thread order for artifact rendering.
            chosen = sorted(candidates, key=lambda m: (-m.usage_count, -(
                m.last_usage_day if m.last_usage_day is not None else m.generated_day), m.thread_id))[:limit]
            chosen = sorted(chosen, key=lambda m: m.thread_id)
            self.index = {f"rollout_summaries/{m.thread_id}.md": m.rollout_summary
                          for m in chosen}
            self.summary = ("v1\n## User Profile\n## User preferences\n"
                            "## General Tips\n## What's in Memory\n" +
                            "\n".join(f"- rollout_summaries/{m.thread_id}.md — {m.rollout_slug}; thread_id={m.thread_id}"
                                      for m in chosen))
            self.watermark = max([self.watermark, *[m.generated_day for m in chosen]])
        finally:
            self.phase2_owner = None

    def read_context(self, *, use_memories: bool, byte_cap: int = 8900) -> tuple[str, str]:
        if not use_memories or not self.summary:
            return "", ""
        # Real Codex uses a token limit plus typed developer fragments.
        return "developer", self.summary.encode("utf-8")[:byte_cap].decode("utf-8", "ignore")

    def lookup_evidence(self, path: str) -> str | None:
        # No speculative lookup and no escape to external paths.
        return self.index.get(path)


def demo() -> None:
    db = ToyMemoryStore()
    a = Rollout("T-01", 98, 4, "interactive", (
        "USER: Run focused tests only", "TOOL: noisy raw stdout",
        "RESULT: 2 tests passed token=private123",))
    b = Rollout("T-02", 99, 5, "interactive", (
        "USER: Audited the auth module", "RESULT: no code changed",))
    fresh = Rollout("T-03", 100, 0, "interactive", ("USER: unfinished",))
    delegated = Rollout("T-04", 99, 10, "subagent", ("USER: child",))
    assert db.claim(a, now_day=100, owner="worker-A")
    assert not db.claim(a, now_day=100, owner="worker-B")
    assert db.claim(b, now_day=100, owner="worker-B")
    assert not db.claim(fresh, now_day=100, owner="worker-C")
    assert not db.claim(delegated, now_day=100, owner="worker-C")
    print("Phase 1: leased two eligible interactive, idle rollouts")

    try:
        db.extract(a, owner="worker-B", version="v2", now_day=100)
    except PermissionError:
        print("Phase 1: duplicate worker cannot complete another lease")
    else:
        raise AssertionError("claim ownership was bypassed")
    v2 = db.extract(a, owner="worker-A", version="v2", now_day=100)
    v1 = db.extract(b, owner="worker-B", version="v1", now_day=100)
    assert v2.raw_memory is None and v1.raw_memory is not None
    assert "private123" not in v2.rollout_summary
    assert "noisy raw stdout" not in v2.rollout_summary
    print("Phase 1: V1/V2 extraction schema differs; secrets redacted")

    assert db.acquire_phase2("consolidator-A")
    assert not db.acquire_phase2("consolidator-B")
    try:
        db.consolidate(owner="consolidator-B", version="v2", now_day=100)
    except PermissionError:
        print("Phase 2: global owner lock prevents parallel consolidation")
    else:
        raise AssertionError("global lock bypassed")
    db.consolidate(owner="consolidator-A", version="v2", now_day=100)
    assert db.phase2_owner is None and db.watermark == 100
    assert list(db.index) == ["rollout_summaries/T-01.md", "rollout_summaries/T-02.md"]
    print("Phase 2: stable memory index created, watermark advanced")

    role, context = db.read_context(use_memories=True)
    assert role == "developer" and "## What's in Memory" in context
    assert "noisy raw stdout" not in context
    assert db.read_context(use_memories=False) == ("", "")
    assert db.lookup_evidence("rollout_summaries/T-01.md") is not None
    assert db.lookup_evidence("rollout_summaries/T-99.md") is None
    assert db.lookup_evidence("../secrets") is None
    print("Read: bounded developer summary; evidence fetched only by exact known path")

    # A stale entry no longer meets the retention window; the next Phase 2
    # selection prunes its index route rather than inventing newer evidence.
    previous = db.stage1["T-01"]
    db.stage1["T-01"] = Stage1(previous.thread_id, 1, previous.rollout_summary,
                               previous.rollout_slug, previous.raw_memory,
                               last_usage_day=1, usage_count=20)
    assert db.acquire_phase2("consolidator-C")
    db.consolidate(owner="consolidator-C", version="v2", now_day=100,
                   max_unused_days=60)
    assert "rollout_summaries/T-01.md" not in db.index
    assert db.lookup_evidence("rollout_summaries/T-01.md") is None
    print("Retention: stale memory entry removed from selected index")
    print("All teaching assertions passed")


if __name__ == "__main__":
    demo()
