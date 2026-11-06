"""Chapter 09: a deterministic policy/approval/sandbox decision simulator.

Python 3.10+, standard library only. No shell, filesystem or network operation.
NOT Codex's real policy evaluator, approval UI, or an OS sandbox.
"""
from dataclasses import dataclass
from enum import Enum


class ApprovalMode(Enum):
    NEVER = "never"
    ON_REQUEST = "on-request"


class Requirement(Enum):
    SKIP = "skip"
    NEEDS_APPROVAL = "needs-approval"
    FORBIDDEN = "forbidden"


@dataclass(frozen=True)
class Request:
    label: str
    operation: str
    target: str
    dangerous: bool = False
    requests_extra_write: bool = False


@dataclass(frozen=True)
class SandboxProfile:
    readable_prefix: str = "workspace/"
    writable_prefix: str = "workspace/src/"
    explicitly_denied_read: str = "workspace/.secrets/"
    extra_write_prefix: str = "workspace/exports/"
    network_allowed: bool = False


@dataclass(frozen=True)
class Outcome:
    status: str
    approval: str
    sandbox: str
    executed: bool


def decide_requirement(request: Request, mode: ApprovalMode) -> Requirement:
    # This is illustrative, not a reimplementation of Codex exec_policy.rs.
    if request.dangerous or request.requests_extra_write:
        return Requirement.FORBIDDEN if mode is ApprovalMode.NEVER else Requirement.NEEDS_APPROVAL
    return Requirement.SKIP


def sandbox_allows(request: Request, profile: SandboxProfile, extra_write_granted: bool) -> bool:
    # A pure-data predicate. Real sandbox restrictions must be OS/executor-enforced.
    if request.operation == "read":
        return (request.target.startswith(profile.readable_prefix)
                and not request.target.startswith(profile.explicitly_denied_read))
    if request.operation == "write":
        return (request.target.startswith(profile.writable_prefix)
                or (extra_write_granted and request.target.startswith(profile.extra_write_prefix)))
    if request.operation == "network":
        return profile.network_allowed
    return False


def assess(request: Request, mode: ApprovalMode, reviewer_approved: bool | None, profile: SandboxProfile) -> Outcome:
    requirement = decide_requirement(request, mode)
    if requirement is Requirement.FORBIDDEN:
        return Outcome("forbidden-by-policy", "not-requested", "not-run", False)
    if requirement is Requirement.NEEDS_APPROVAL and reviewer_approved is not True:
        return Outcome("rejected-by-reviewer", "denied", "not-run", False)

    approval = "approved" if requirement is Requirement.NEEDS_APPROVAL else "skipped"
    extra_write_granted = request.requests_extra_write and approval == "approved"
    if not sandbox_allows(request, profile, extra_write_granted):
        return Outcome("sandbox-denied", approval, "denied", False)
    # Pretend execution succeeded. No real executable is ever launched.
    return Outcome("simulated-success", approval, "allowed", True)


def main() -> None:
    profile = SandboxProfile()
    scenarios = [
        (Request("safe-read", "read", "workspace/src/login.py"), ApprovalMode.ON_REQUEST, None, "simulated-success"),
        (Request("safe-write", "write", "workspace/src/fix.py"), ApprovalMode.ON_REQUEST, None, "simulated-success"),
        (Request("denied-secret", "read", "workspace/.secrets/key"), ApprovalMode.NEVER, None, "sandbox-denied"),
        (Request("dangerous-never", "write", "workspace/src/x", dangerous=True), ApprovalMode.NEVER, None, "forbidden-by-policy"),
        (Request("dangerous-rejected", "write", "workspace/src/x", dangerous=True), ApprovalMode.ON_REQUEST, False, "rejected-by-reviewer"),
        (Request("approved-not-unrestricted", "write", "workspace/exports/log.txt", dangerous=True), ApprovalMode.ON_REQUEST, True, "sandbox-denied"),
        (Request("scoped-extension", "write", "workspace/exports/log.txt", requests_extra_write=True), ApprovalMode.ON_REQUEST, True, "simulated-success"),
        (Request("network-off", "network", "example.test"), ApprovalMode.ON_REQUEST, None, "sandbox-denied"),
    ]
    for req, mode, reviewer, expected in scenarios:
        outcome = assess(req, mode, reviewer, profile)
        assert outcome.status == expected, (req.label, outcome.status, expected)
        print(f"{req.label:27} policy={mode.value:10} approval={outcome.approval:13} sandbox={outcome.sandbox:7} => {outcome.status}")
    assert assess(Request("secret-after-approval", "read", "workspace/.secrets/key", dangerous=True), ApprovalMode.ON_REQUEST, True, profile).status == "sandbox-denied"
    print("Explicit denied-read remains denied after simulated approval")
    print("All teaching assertions passed")


if __name__ == "__main__":
    main()
