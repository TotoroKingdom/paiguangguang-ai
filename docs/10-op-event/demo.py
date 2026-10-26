"""Chapter 10: typed operations and correlated events, a deterministic toy.

Python 3.10+. Pure asyncio queues; no actual Codex protocol, model, tool,
network, approval UI, or OS subprocess. Never start real shell commands.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass


@dataclass(frozen=True)
class Op:
    kind: str
    turn_id: str
    value: str = ""


@dataclass(frozen=True)
class Event:
    turn_id: str
    kind: str
    detail: str = ""


class FakeCore:
    def __init__(self) -> None:
        # Bounded submission queue vs independently consumed event stream.
        self.ops: asyncio.Queue[Op] = asyncio.Queue(maxsize=8)
        self.events: asyncio.Queue[Event] = asyncio.Queue()
        self._decision: dict[str, asyncio.Future[bool]] = {}
        self._active: dict[str, asyncio.Task[None]] = {}
        self._turn_index = 0

    async def submit_turn(self, user_text: str) -> str:
        self._turn_index += 1
        turn_id = f"turn-{self._turn_index}"
        await self.ops.put(Op("TURN_INPUT", turn_id, user_text))
        return turn_id  # Request acceptance, NOT completion.

    async def submit(self, op: Op) -> None:
        await self.ops.put(op)

    async def serve(self) -> None:
        while True:
            op = await self.ops.get()
            if op.kind == "STOP":
                for task in self._active.values():
                    if not task.done():
                        task.cancel()
                return
            if op.kind == "TURN_INPUT":
                task = asyncio.create_task(self._run_turn(op))
                self._active[op.turn_id] = task
            elif op.kind == "APPROVAL_RESPONSE":
                decision = self._decision.get(op.turn_id)
                if decision is not None and not decision.done():
                    decision.set_result(op.value == "approve")
            elif op.kind == "INTERRUPT":
                task = self._active.get(op.turn_id)
                if task is not None and not task.done():
                    task.cancel()
            else:
                raise ValueError(f"unknown fake op: {op.kind}")

    async def _emit(self, turn_id: str, kind: str, detail: str = "") -> None:
        await self.events.put(Event(turn_id, kind, detail))

    async def _run_turn(self, op: Op) -> None:
        turn_id = op.turn_id
        try:
            await self._emit(turn_id, "TurnStarted", op.value)
            await self._emit(turn_id, "ExecCommandBegin", "simulated check")
            decision = asyncio.get_running_loop().create_future()
            self._decision[turn_id] = decision
            await self._emit(turn_id, "ExecApprovalRequest", "call-1")
            approved = await decision
            if approved:
                await self._emit(turn_id, "ExecCommandOutputDelta", "tests: 2 passed (fixture)")
                await self._emit(turn_id, "ExecCommandEnd", "exit=0")
                await self._emit(turn_id, "AgentMessage", "检查结束（预置内容）")
            else:
                await self._emit(turn_id, "ExecCommandEnd", "not executed: denied")
                await self._emit(turn_id, "AgentMessage", "审批拒绝，未执行命令")
            await self._emit(turn_id, "TurnComplete", "finished")
        except asyncio.CancelledError:
            await self._emit(turn_id, "TurnAborted", "interrupted")
        finally:
            self._decision.pop(turn_id, None)


async def demo() -> None:
    core = FakeCore()
    server = asyncio.create_task(core.serve())
    seen: dict[str, list[str]] = {}
    for response_to_approval in ("approve", "deny", "interrupt"):
        turn_id = await core.submit_turn(f"check login ({response_to_approval})")
        print(f"AppServer turn/start ACK: {turn_id}; terminal event not received")
        assert turn_id not in seen
        kinds: list[str] = []
        while True:
            event = await asyncio.wait_for(core.events.get(), timeout=3)
            assert event.turn_id == turn_id, "cross-turn event misrouting"
            kinds.append(event.kind)
            print(f"  [{event.turn_id}] {event.kind}: {event.detail}")
            if event.kind == "ExecApprovalRequest":
                # An approval response travels BACK to Core; an event is not an Op.
                if response_to_approval == "interrupt":
                    await core.submit(Op("INTERRUPT", turn_id))
                else:
                    await core.submit(Op("APPROVAL_RESPONSE", turn_id, response_to_approval))
            if event.kind in ("TurnComplete", "TurnAborted"):
                break
        seen[turn_id] = kinds

    assert seen["turn-1"] == [
        "TurnStarted", "ExecCommandBegin", "ExecApprovalRequest",
        "ExecCommandOutputDelta", "ExecCommandEnd", "AgentMessage", "TurnComplete",
    ]
    assert seen["turn-2"] == [
        "TurnStarted", "ExecCommandBegin", "ExecApprovalRequest",
        "ExecCommandEnd", "AgentMessage", "TurnComplete",
    ]
    assert seen["turn-3"] == [
        "TurnStarted", "ExecCommandBegin", "ExecApprovalRequest", "TurnAborted",
    ]
    await core.submit(Op("STOP", ""))
    await server
    print("All teaching assertions passed")


if __name__ == "__main__":
    asyncio.run(demo())
