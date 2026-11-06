"""Final chapter: a deterministic, OFFLINE end-to-end Codex-like request trace.

Python 3.10+, stdlib only. Fake model/tools, in-memory worktree, temp JSONL
rollout; no Codex binaries, API keys, shell, network, or real source edits.
This is an *architecture experiment*, not a capture of an actual Codex run.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import os


THREAD_ID, TURN_ID = "thread-demo-1", "turn-demo-1"


@dataclass(frozen=True)
class Event:
    seq: int
    kind: str
    thread_id: str
    turn_id: str
    step: int
    call_id: str | None
    detail: str


class TraceRecorder:
    """UI events are observable immediately; JSONL requires explicit flush."""

    def __init__(self, path: Path):
        self.path = path
        self.pending: list[Event] = []
        self.ui_events: list[Event] = []

    def emit(self, kind: str, step: int, detail: str = "", call_id: str | None = None) -> Event:
        event = Event(len(self.ui_events) + 1, kind, THREAD_ID, TURN_ID, step, call_id, detail)
        self.ui_events.append(event)
        self.pending.append(event)
        return event

    def flush(self) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            for event in self.pending:
                f.write(json.dumps(asdict(event), ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())
        self.pending.clear()

    def reopen(self) -> list[dict]:
        if not self.path.exists():
            return []
        return [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines()]


@dataclass(frozen=True)
class ToolCall:
    name: str
    call_id: str
    arg: str


class ScriptedModel:
    """Scripted responses imitate successive model samples, not an actual LLM."""

    def sample(self, history: list[tuple[str, str]], step: int) -> ToolCall | str:
        observations = [text for kind, text in history if kind == "tool"]
        if not observations:
            return ToolCall("read_file", f"call-{step}", "src/login.py")
        if "patch: denied" in observations:
            return "已读取代码，但修改未获批准；未修改文件，也未声称测试通过。"
        if not any(x.startswith("patch: applied") for x in observations):
            return ToolCall("apply_patch", f"call-{step}", "src/login.py")
        if not any(x.startswith("test:") for x in observations):
            return ToolCall("run_related_tests", f"call-{step}", "tests/test_login.py")
        if "test: passed" in observations:
            return "已修复登录校验并验证相关测试通过（离线模拟）。"
        return "测试未通过，任务尚未完成。"


class ToyTools:
    def __init__(self):
        self.files = {"src/login.py": "def login(password): return password == 'wrong'"}
        self.execution_counts: dict[str, int] = {}

    def execute(self, call: ToolCall, *, approved: bool, sandbox_roots: tuple[str, ...]) -> str:
        self.execution_counts[call.name] = self.execution_counts.get(call.name, 0) + 1
        if call.name == "read_file":
            return "read: " + self.files[call.arg]
        if call.name == "apply_patch":
            if not approved:
                return "patch: denied"
            if not any(call.arg.startswith(root) for root in sandbox_roots):
                return "patch: sandbox-denied"
            self.files[call.arg] = self.files[call.arg].replace("'wrong'", "'correct'")
            return "patch: applied"
        if call.name == "run_related_tests":
            passed = "'correct'" in self.files["src/login.py"]
            return "test: passed" if passed else "test: failed"
        return "tool: unknown"


class MiniRuntime:
    def __init__(self, recorder: TraceRecorder, *, approve_patch: bool, cancel_at_step: int = 0):
        self.recorder, self.approve_patch, self.cancel_at_step = recorder, approve_patch, cancel_at_step
        self.tools = ToyTools()
        self.model = ScriptedModel()
        self.history: list[tuple[str, str]] = []

    def run(self) -> str:
        e = self.recorder.emit
        e("OpUserTurn", 0, "修复登录判断并运行相关测试")
        e("TurnStarted", 0, "turn admitted")
        self.history.append(("user", "修复登录判断并运行相关测试"))
        for step in range(1, 9):
            if step == self.cancel_at_step:
                e("TurnAborted", step, "user interrupted before sampling")
                self.recorder.flush()
                return "aborted"
            e("PromptPrepared", step, f"history_items={len(self.history)}")
            e("ModelStreamStarted", step, "scripted stream")
            response = self.model.sample(self.history, step)
            if isinstance(response, str):
                e("AssistantFinal", step, response)
                self.history.append(("assistant", response))
                e("TurnComplete", step, "successful lifecycle completion")
                self.recorder.flush()
                return response
            call = response
            e("ModelFunctionCall", step, f"{call.name}({call.arg})", call.call_id)
            approval = True
            if call.name == "apply_patch":
                e("ApprovalRequested", step, "patch requires approval", call.call_id)
                approval = self.approve_patch
                e("ApprovalResolved", step, "approved" if approval else "denied", call.call_id)
            result = self.tools.execute(call, approved=approval, sandbox_roots=("src/",))
            e("ToolResult", step, result, call.call_id)
            self.history.append(("tool", result))
            e("SampleNeedsFollowUp", step, "tool observation added")
        raise AssertionError("scripted agent exceeded step limit")


def assert_valid_trace(events: list[dict], *, expected_terminal: str) -> None:
    kinds = [e["kind"] for e in events]
    assert kinds[0] == "OpUserTurn"
    assert "TurnStarted" in kinds
    assert kinds[-1] == expected_terminal
    assert kinds.count("TurnComplete") + kinds.count("TurnAborted") == 1
    assert [e["seq"] for e in events] == list(range(1, len(events) + 1))
    assert all(e["thread_id"] == THREAD_ID and e["turn_id"] == TURN_ID for e in events)
    requested = {e["call_id"] for e in events if e["kind"] == "ModelFunctionCall"}
    results = {e["call_id"] for e in events if e["kind"] == "ToolResult"}
    assert requested == results
    for e in events:
        if e["kind"] in ("ApprovalRequested", "ApprovalResolved"):
            assert e["call_id"] in requested


def main() -> None:
    with TemporaryDirectory() as root:
        recorder = TraceRecorder(Path(root) / "approved.jsonl")
        completed = MiniRuntime(recorder, approve_patch=True)
        answer = completed.run()
        events = recorder.reopen()
        assert_valid_trace(events, expected_terminal="TurnComplete")
        assert "测试通过" in answer and "'correct'" in completed.tools.files["src/login.py"]
        assert completed.tools.execution_counts == {
            "read_file": 1, "apply_patch": 1, "run_related_tests": 1
        }
        assert sum(e["kind"] == "ModelStreamStarted" for e in events) == 4
        print("CASE A: Approved: 4 samples, read -> patch -> test -> final")
        for e in events:
            if e["kind"] in ("ModelFunctionCall", "ApprovalResolved", "ToolResult", "TurnComplete"):
                print(f"  [{e['seq']:02d}] step={e['step']} {e['kind']} call={e['call_id']} {e['detail']}")

        denied_recorder = TraceRecorder(Path(root) / "denied.jsonl")
        denied = MiniRuntime(denied_recorder, approve_patch=False)
        denial_answer = denied.run()
        denial_events = denied_recorder.reopen()
        assert_valid_trace(denial_events, expected_terminal="TurnComplete")
        assert "未获批准" in denial_answer
        assert "'wrong'" in denied.tools.files["src/login.py"]
        assert "run_related_tests" not in denied.tools.execution_counts
        print("CASE B: Approval denied: TurnComplete is possible; patch was not applied")

        aborted_recorder = TraceRecorder(Path(root) / "aborted.jsonl")
        aborted = MiniRuntime(aborted_recorder, approve_patch=True, cancel_at_step=2)
        assert aborted.run() == "aborted"
        abort_events = aborted_recorder.reopen()
        assert_valid_trace(abort_events, expected_terminal="TurnAborted")
        assert "'wrong'" in aborted.tools.files["src/login.py"]
        assert "apply_patch" not in aborted.tools.execution_counts
        print("CASE C: Cancelled: TurnAborted, not TurnComplete or silently successful")

        buffered = TraceRecorder(Path(root) / "buffered.jsonl")
        buffered.emit("UIEvent", 0, "visible but not yet durable")
        assert len(buffered.ui_events) == 1 and buffered.reopen() == []
        buffered.flush()
        assert len(buffered.reopen()) == 1
        print("CASE D: UI observation precedes explicit durable JSONL flush")
        print("All teaching assertions passed")


if __name__ == "__main__":
    main()
