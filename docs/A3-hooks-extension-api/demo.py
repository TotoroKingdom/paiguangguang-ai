"""A3: deterministic offline illustration of Codex Hooks and Extension API.

Python 3.10+; standard library only.
No shell process, MCP server, model, network, policy changes or filesystem writes.
This is NOT an implementation of Codex hook JSON wire formats or its sandbox.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(frozen=True)
class Hook:
    name: str
    event: str
    action: str = "observe"  # observe/deny/allow/rewrite/stop/feedback
    matcher: str = "*"
    completed_tick: int = 0  # Simulated completion order, NOT wall time.
    value: str = ""
    background: bool = False


@dataclass
class Outcome:
    ran: list[str] = field(default_factory=list)
    scheduled: list[str] = field(default_factory=list)
    blocked: bool = False
    stop: bool = False
    permission: str | None = None
    updated_input: dict[str, Any] | None = None
    feedback: list[str] = field(default_factory=list)


class ToyHooks:
    def __init__(self, hooks: list[Hook]):
        self.hooks = list(hooks)

    def dispatch(self, event: str, tool: str = "") -> Outcome:
        outcome = Outcome()
        matches = [h for h in self.hooks
                   if h.event == event and h.matcher in ("*", tool)]
        foreground = []
        for index, hook in enumerate(matches):
            if hook.background:
                outcome.scheduled.append(hook.name)
            else:
                foreground.append((index, hook))
        # Real dispatcher executes sync hooks concurrently and reports them
        # in configured order; this toy records a separate completion order.
        completion = sorted(foreground, key=lambda x: (x[1].completed_tick, x[0]))
        outcome.ran = [h.name for _, h in foreground]
        if event == "PreToolUse":
            outcome.blocked = any(h.action == "deny" for _, h in foreground)
            if not outcome.blocked:
                updated = [h for _, h in completion if h.action == "rewrite"]
                if updated:
                    outcome.updated_input = {"query": updated[-1].value}
        elif event == "PermissionRequest":
            decisions = [h.action for _, h in foreground if h.action in ("allow", "deny")]
            outcome.permission = ("deny" if "deny" in decisions
                                  else "allow" if "allow" in decisions else None)
        elif event in ("PostToolUse", "PreCompact", "PostCompact"):
            outcome.stop = any(h.action == "stop" for _, h in foreground)
            outcome.feedback = [h.value for _, h in foreground if h.action == "feedback"]
        return outcome


@dataclass(frozen=True)
class ToolRun:
    status: str
    executed: bool
    input_used: dict[str, str]
    notes: tuple[str, ...] = ()


class ToyRuntime:
    def __init__(self, hooks: ToyHooks):
        self.hooks = hooks
        self.tool_calls = 0
        self.compaction_count = 0

    def tool_call(self, tool: str, query: str, *,
                  approval_required: bool = False,
                  user_approved: bool = False,
                  sandbox_allowed: bool = True) -> ToolRun:
        args = {"query": query}
        before = self.hooks.dispatch("PreToolUse", tool)
        if before.blocked:
            return ToolRun("pre-hook-blocked", False, args)
        if before.updated_input is not None:
            args = before.updated_input
        if approval_required:
            decision = self.hooks.dispatch("PermissionRequest", tool).permission
            if decision == "deny":
                return ToolRun("permission-hook-denied", False, args)
            if decision != "allow" and not user_approved:
                return ToolRun("approval-not-granted", False, args)
        # Hook approval cannot override the separate sandbox/resource guard.
        if not sandbox_allowed:
            return ToolRun("sandbox-denied", False, args)
        self.tool_calls += 1  # A stub, not a real tool call.
        after = self.hooks.dispatch("PostToolUse", tool)
        if after.stop:
            return ToolRun("post-hook-stopped", True, args, tuple(after.feedback))
        return ToolRun("completed", True, args, tuple(after.feedback))

    def compact(self, trigger: str) -> tuple[bool, bool]:
        if self.hooks.dispatch("PreCompact", trigger).stop:
            return False, False
        self.compaction_count += 1  # Purely simulated compaction.
        post_stopped = self.hooks.dispatch("PostCompact", trigger).stop
        return True, post_stopped


class ToyExtensionRegistry:
    """Separate HOST contributor mechanism; not a user command hook."""

    def __init__(self) -> None:
        self.tool_contributors: list[Callable[[], str]] = []
        self.turn_lifecycle: list[Callable[[str], str]] = []

    def register_tool(self, contributor: Callable[[], str]) -> None:
        self.tool_contributors.append(contributor)

    def register_turn(self, contributor: Callable[[str], str]) -> None:
        self.turn_lifecycle.append(contributor)

    def tool_names(self) -> list[str]:
        return [c() for c in self.tool_contributors]

    def turn_events(self, phase: str) -> list[str]:
        return [c(phase) for c in self.turn_lifecycle]


def main() -> None:
    print("Scenario 1: pre-tool rewrite: last completed, not last configured")
    engine = ToyHooks([
        Hook("slow-rewrite", "PreToolUse", "rewrite", "search", 9, "slow"),
        Hook("fast-rewrite", "PreToolUse", "rewrite", "search", 1, "fast"),
        Hook("observer", "PreToolUse", background=True),
        Hook("post-note", "PostToolUse", "feedback", "search", value="observed"),
    ])
    pre = engine.dispatch("PreToolUse", "search")
    assert pre.ran == ["slow-rewrite", "fast-rewrite"]
    assert pre.scheduled == ["observer"]
    assert pre.updated_input == {"query": "slow"}
    runtime = ToyRuntime(engine)
    ok = runtime.tool_call("search", "original")
    assert ok.executed and ok.input_used["query"] == "slow"
    assert ok.status == "completed" and ok.notes == ("observed",)
    print("  latest completion rewrite -> slow; background observer not a gate")

    print("Scenario 2: pre-tool deny wins over an input rewrite")
    denied = ToyRuntime(ToyHooks([
        Hook("rewriter", "PreToolUse", "rewrite", "delete", 4, "replacement"),
        Hook("deny-delete", "PreToolUse", "deny", "delete", 2),
    ]))
    blocked = denied.tool_call("delete", "danger")
    assert blocked.status == "pre-hook-blocked" and not blocked.executed
    assert denied.tool_calls == 0
    print("  blocked before tool execution")

    print("Scenario 3: permission deny overrides allow")
    reviewer = ToyRuntime(ToyHooks([
        Hook("allow", "PermissionRequest", "allow", "write"),
        Hook("deny", "PermissionRequest", "deny", "write"),
    ]))
    outcome = reviewer.tool_call("write", "x", approval_required=True, user_approved=True)
    assert outcome.status == "permission-hook-denied" and not outcome.executed
    assert ToyRuntime(ToyHooks([])).tool_call("write", "x", approval_required=True).status == "approval-not-granted"
    print("  deny takes precedence; no decision needs another approval path")

    print("Scenario 4: permission hook does not bypass sandbox")
    allowed = ToyRuntime(ToyHooks([Hook("allow", "PermissionRequest", "allow", "write")]))
    safety = allowed.tool_call("write", "x", approval_required=True, sandbox_allowed=False)
    assert safety.status == "sandbox-denied" and not safety.executed
    print("  resource restriction remains effective")

    print("Scenario 5: post-tool stop cannot undo a completed tool call")
    finished = ToyRuntime(ToyHooks([
        Hook("stop", "PostToolUse", "stop", "search"),
    ]))
    post = finished.tool_call("search", "x")
    assert post.executed and post.status == "post-hook-stopped"
    assert finished.tool_calls == 1
    print("  side effect already simulated; only subsequent flow is stopped")

    print("Scenario 6: compaction before vs after hook")
    compact = ToyRuntime(ToyHooks([
        Hook("stop-auto", "PreCompact", "stop", "auto"),
        Hook("stop-after", "PostCompact", "stop", "manual"),
    ]))
    assert compact.compact("auto") == (False, False)
    assert compact.compaction_count == 0
    assert compact.compact("manual") == (True, True)
    assert compact.compaction_count == 1
    print("  pre stopped compaction; post stopped after compaction")

    print("Scenario 7: host ExtensionRegistry contributors are separate")
    registry = ToyExtensionRegistry()
    registry.register_tool(lambda: "native_audit_tool")
    registry.register_turn(lambda phase: f"turn:{phase}")
    assert registry.tool_names() == ["native_audit_tool"]
    assert registry.turn_events("start") == ["turn:start"]
    print("  host tool and lifecycle contributors registered")

    print("All teaching assertions passed")


if __name__ == "__main__":
    main()
