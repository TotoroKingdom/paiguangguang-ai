"""Chapter 08: safe, deterministic shell-execution lifecycle demonstration.

Python 3.10+; standard library only. Actually spawns a *fixed* Python child
process for permitted examples. Does NOT implement Codex approvals or sandbox.
Never executes arbitrary user/model shell strings and never writes files.
"""
from dataclasses import dataclass
from pathlib import Path
import subprocess
import sys


@dataclass(frozen=True)
class ExecCall:
    call_id: str
    action: str
    timeout_ms: int = 8000


@dataclass(frozen=True)
class ExecResult:
    call_id: str
    status: str
    launched: bool
    exit_code: int | None
    stdout: str = ""
    stderr: str = ""


class TeachingApprovalGate:
    """This is a static teaching decision, NOT actual user approval."""

    @staticmethod
    def admit(action: str) -> bool:
        return action != "needs_approval"


class AllowlistedExecHandler:
    """Directly spawns only one of several pre-written, harmless programs."""

    _programs = {
        "inspect": "print('login module: inspected (simulated)')",
        "run_tests": "print('tests: 2 passed (simulated)')",
        "nonzero": "import sys; print('test failed', file=sys.stderr); sys.exit(3)",
        "timeout": "import time; time.sleep(10)",
        "needs_approval": "print('this should never run')",
    }

    def run(self, call: ExecCall) -> ExecResult:
        print(f"[{call.call_id}] requested: {call.action}")
        if call.action not in self._programs:
            return ExecResult(call.call_id, "unsupported", False, None)
        if not TeachingApprovalGate.admit(call.action):
            return ExecResult(call.call_id, "denied", False, None)
        if not 50 <= call.timeout_ms <= 20000:
            return ExecResult(call.call_id, "invalid_timeout", False, None)

        # A fixed interpreter executable, fixed script, shell=False.
        # cwd is explicit; no sandbox or filesystem restrictions are claimed.
        try:
            completed = subprocess.run(
                [sys.executable, "-I", "-c", self._programs[call.action]],
                cwd=Path.cwd(),
                capture_output=True,
                text=True,
                timeout=call.timeout_ms / 1000,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return ExecResult(call.call_id, "timed_out", True, None)
        return ExecResult(
            call_id=call.call_id,
            status="completed" if completed.returncode == 0 else "exited_nonzero",
            launched=True,
            exit_code=completed.returncode,
            stdout=completed.stdout.strip()[:160],
            stderr=completed.stderr.strip()[:160],
        )


def main() -> None:
    handler = AllowlistedExecHandler()
    calls = [
        ExecCall("call-1", "inspect"),
        ExecCall("call-2", "run_tests"),
        ExecCall("call-3", "nonzero"),
        ExecCall("call-4", "needs_approval"),
        ExecCall("call-5", "timeout", timeout_ms=200),
        ExecCall("call-6", "arbitrary_shell_string"),
    ]
    results = [handler.run(call) for call in calls]
    for result in results:
        print(
            f"[{result.call_id}] status={result.status}; launched={result.launched}; "
            f"exit={result.exit_code}; stdout={result.stdout!r}; stderr={result.stderr!r}"
        )

    assert [r.status for r in results] == [
        "completed", "completed", "exited_nonzero", "denied", "timed_out", "unsupported"
    ]
    assert [r.launched for r in results] == [True, True, True, False, True, False]
    assert results[2].exit_code == 3
    assert results[4].exit_code is None
    assert [r.call_id for r in results] == [call.call_id for call in calls]
    print("All teaching assertions passed")


if __name__ == "__main__":
    main()
