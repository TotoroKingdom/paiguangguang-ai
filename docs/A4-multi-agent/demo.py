"""A4: offline Multi-Agent orchestration, snapshot inheritance and safe merge.

Python 3.10+, stdlib only. This is NOT Codex's Rust AgentControl or its
real collaboration protocol. No model, network, shell or file writes.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from enum import Enum


class State(str, Enum):
    ACCEPTED = "accepted"
    RUNNING = "running"
    COMPLETED = "completed"
    INTERRUPTED = "interrupted"


@dataclass(frozen=True)
class PermissionSnapshot:
    cwd: str
    approval_mode: str
    write_roots: frozenset[str]
    model: str


@dataclass(frozen=True)
class Job:
    name: str
    duration_ticks: int
    read_set: frozenset[str]
    write_set: frozenset[str]
    answer: str


@dataclass
class Agent:
    id: str
    parent: str
    depth: int
    snapshot: PermissionSnapshot
    job: Job
    state: State = State.ACCEPTED
    task: asyncio.Task[None] | None = None
    mailbox: asyncio.Queue[str] = field(default_factory=asyncio.Queue)
    result: str | None = None


class ToyAgentControl:
    def __init__(self, *, max_depth: int, max_agents: int):
        self.max_depth, self.max_agents = max_depth, max_agents
        self.agents: dict[str, Agent] = {}
        self.events: asyncio.Queue[tuple[str, State]] = asyncio.Queue()
        self._next_id = 0

    async def spawn(self, parent: str, parent_depth: int,
                    parent_snapshot: PermissionSnapshot, job: Job) -> Agent:
        if parent_depth + 1 > self.max_depth:
            raise ValueError("depth limit")
        if len(self.agents) >= self.max_agents:
            raise ValueError("agent capacity")
        # A role can change a task objective, but this toy does not grant more rights.
        for existing in self.agents.values():
            if existing.state in (State.ACCEPTED, State.RUNNING):
                conflict = (job.write_set & (existing.job.write_set | existing.job.read_set)) | (
                    existing.job.write_set & job.read_set
                )
                if conflict:
                    raise ValueError("shared workspace conflict: " + ", ".join(sorted(conflict)))
        self._next_id += 1
        agent = Agent(f"child-{self._next_id}", parent, parent_depth + 1,
                      parent_snapshot, job)
        self.agents[agent.id] = agent
        await self.events.put((agent.id, State.ACCEPTED))
        agent.task = asyncio.create_task(self._run(agent))
        return agent  # Acceptance != completion.

    async def _run(self, agent: Agent) -> None:
        try:
            agent.state = State.RUNNING
            await self.events.put((agent.id, State.RUNNING))
            for _ in range(agent.job.duration_ticks):
                await asyncio.sleep(0)
            agent.result = agent.job.answer
            agent.state = State.COMPLETED
        except asyncio.CancelledError:
            agent.state = State.INTERRUPTED
        finally:
            await self.events.put((agent.id, agent.state))

    async def send_message(self, agent_id: str, message: str) -> None:
        """QueueOnly style: enqueue a message, not a new task or forced interrupt."""
        await self.agents[agent_id].mailbox.put(message)

    async def interrupt(self, agent_id: str) -> None:
        agent = self.agents[agent_id]
        if agent.task and not agent.task.done():
            agent.task.cancel()
            await agent.task

    async def wait_any(self, targets: set[str], timeout: float) -> tuple[str, State] | None:
        """Teaching approximation of v1 final-status wait; not v2 mailbox wait."""
        pending = {x for x in targets if self.agents[x].state not in
                   (State.COMPLETED, State.INTERRUPTED)}
        if not pending:
            agent_id = sorted(targets)[0]
            return agent_id, self.agents[agent_id].state
        while True:
            try:
                agent_id, state = await asyncio.wait_for(self.events.get(), timeout)
            except asyncio.TimeoutError:
                return None
            if agent_id in targets and state in (State.COMPLETED, State.INTERRUPTED):
                return agent_id, state

    def collect(self, agent_id: str) -> str:
        a = self.agents[agent_id]
        if a.state is not State.COMPLETED or a.result is None:
            raise ValueError("result not ready")
        return a.result


def main() -> None:
    asyncio.run(experiment())


async def experiment() -> None:
    snapshot = PermissionSnapshot(
        cwd="/workspace", approval_mode="on-request",
        write_roots=frozenset({"/workspace/reports"}), model="model-A"
    )
    control = ToyAgentControl(max_depth=1, max_agents=3)
    audit = await control.spawn("parent", 0, snapshot, Job(
        "security-audit", 25, frozenset({"auth.py"}), frozenset(), "Audit: read-only findings"
    ))
    tests = await control.spawn("parent", 0, snapshot, Job(
        "test-review", 25, frozenset({"tests.py"}), frozenset(), "Tests: read-only findings"
    ))
    assert audit.state in (State.ACCEPTED, State.RUNNING)
    assert audit.result is None and tests.result is None
    assert audit.snapshot is snapshot and tests.snapshot is snapshot
    print("spawn ACK: accepted; outputs not completed; policy snapshot inherited")

    try:
        await control.spawn("parent", 0, snapshot, Job(
            "unsafe-write", 2, frozenset(), frozenset({"auth.py"}), "write"
        ))
    except ValueError as ex:
        assert "workspace conflict" in str(ex)
        print("shared-workspace conflict rejected")
    else:
        raise AssertionError("shared writes should have been rejected")

    try:
        await control.spawn(audit.id, audit.depth, snapshot, Job(
            "grandchild", 1, frozenset(), frozenset(), "grandchild"
        ))
    except ValueError as ex:
        assert "depth limit" in str(ex)
        print("depth limit rejected grandchild")
    else:
        raise AssertionError("depth limit bypassed")

    await control.send_message(audit.id, "Please include exact evidence")
    assert await audit.mailbox.get() == "Please include exact evidence"
    assert audit.result is None
    print("queue-only message delivered without implying completion")

    # Deterministically demonstrate nonterminal wait without external timers.
    early = await control.wait_any({audit.id, tests.id}, timeout=0)
    assert early is None
    print("short wait: timed out; agent remains running")

    await asyncio.gather(audit.task, tests.task)
    assert audit.state is State.COMPLETED and tests.state is State.COMPLETED
    evidence = {a.job.name: control.collect(a.id) for a in (audit, tests)}
    assert evidence == {
        "security-audit": "Audit: read-only findings",
        "test-review": "Tests: read-only findings",
    }
    print("fan-in: both read-only results collected by parent")

    hanging = await control.spawn("parent", 0, snapshot, Job(
        "long-running", 2000, frozenset(), frozenset(), "not reached"
    ))
    await asyncio.sleep(0)  # Allow coroutine to enter its cancellation handler.
    await control.interrupt(hanging.id)
    assert hanging.state is State.INTERRUPTED
    try:
        control.collect(hanging.id)
    except ValueError:
        print("interrupted child has no completed result")
    else:
        raise AssertionError("interrupted child returned completed result")
    print("All teaching assertions passed")


if __name__ == "__main__":
    main()
