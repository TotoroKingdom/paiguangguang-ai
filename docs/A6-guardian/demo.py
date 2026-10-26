"""A6 Guardian: offline risk-score / approval routing / authorization snapshot demo.

Python 3.10+ stdlib. No LLM, MCP, shell, network, filesystem changes, or
actual security enforcement. NOT the Codex Guardian API or actual classifier.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import json


class Decision(str, Enum):
    APPROVED = "approved"
    DENIED = "denied"
    ASK_USER = "ask-user"
    ABORT = "abort"


@dataclass(frozen=True)
class Action:
    call_id: str
    category: str
    resource: str
    auth_version: int
    needs_approval: bool = True


@dataclass(frozen=True)
class Score:
    action_risk: float
    authorization_version: int
    call_id: str
    lag: int = 0
    oversized: bool = False
    failed_unscored: bool = False
    covered: bool = True


@dataclass(frozen=True)
class Assessment:
    outcome: str  # allow / deny
    rationale: str


@dataclass
class Audit:
    call_id: str
    reason: str
    decision: Decision
    review_attempts: int


@dataclass
class ToyGuardian:
    review_threshold: float = 0.3
    max_lag: int = 2
    reviewer_mode: str = "auto"  # auto / user
    policy_mode: str = "adaptive"  # adaptive / required / disabled
    audit: list[Audit] = field(default_factory=list)
    executed: list[str] = field(default_factory=list)

    def cached_evidence(self, action: Action, score: Score | None) -> str:
        """Report why an adaptive fast approval is valid or needs review."""
        if score is None:
            return "missing-score"
        if score.oversized or score.failed_unscored:
            return "scoring-failure"
        if score.lag > self.max_lag:
            return "stale-score"
        if score.authorization_version != action.auth_version:
            return "authorization-changed"
        if not score.covered or score.call_id != action.call_id:
            return "action-not-covered"
        if not 0 <= score.action_risk <= 1:
            return "invalid-score"
        if score.action_risk >= self.review_threshold:
            return "elevated-risk"
        return "low-risk"

    def review(self, action: Action, *, score: Score | None = None,
               synchronous_answers: tuple[str, ...] = (),
               require_fresh: bool = False, required_guardian: bool = False,
               cancelled: bool = False, max_attempts: int = 2) -> Decision:
        """Teaching routing: fast scoring, then human/synchronous review.

        A 'transport' answer simulates a retryable backend failure, while
        malformed/invalid output yields a failure here (never unconditional allow).
        """
        reason = "not-required"
        attempts = 0
        if cancelled:
            decision = Decision.ABORT
            reason = "cancelled"
        elif not action.needs_approval:
            decision = Decision.APPROVED
        elif self.reviewer_mode == "user" and not required_guardian:
            decision = Decision.ASK_USER
            reason = "user-review-configured"
        elif self.policy_mode == "disabled" and not required_guardian:
            decision = Decision.ASK_USER
            reason = "guardian-disabled"
        else:
            if self.policy_mode == "adaptive" and not require_fresh:
                reason = self.cached_evidence(action, score)
            else:
                reason = "fresh-required" if require_fresh else "policy-review"
            if reason == "low-risk":
                decision = Decision.APPROVED
            else:
                decision = Decision.ASK_USER  # no silent allow on missing review
                for raw in synchronous_answers[:max_attempts]:
                    attempts += 1
                    if raw == "transport":
                        reason = "retryable-transport"
                        continue
                    try:
                        obj = json.loads(raw)
                        if obj["outcome"] == "allow":
                            decision = Decision.APPROVED
                            reason = "synchronous-allow"
                        elif obj["outcome"] == "deny":
                            decision = Decision.DENIED
                            reason = "synchronous-deny"
                        else:
                            raise ValueError("invalid outcome")
                    except (ValueError, KeyError, TypeError):
                        reason = "invalid-assessment"
                    break
        self.audit.append(Audit(action.call_id, reason, decision, attempts))
        return decision

    def try_execute(self, action: Action, decision: Decision, *,
                    sandbox_allowed: bool, upstream_allowed: bool) -> str:
        # These checks are NOT implemented by the scoring model. The runtime
        # and upstream system independently control resources and data access.
        if decision is not Decision.APPROVED:
            return "approval-not-granted"
        if not sandbox_allowed:
            return "sandbox-denied"
        if not upstream_allowed:
            return "upstream-data-denied"
        self.executed.append(action.call_id)
        return "executed"


def main() -> None:
    action = Action("call-1", "mcp", "crm/customers", 5)
    g = ToyGuardian()
    low = Score(0.12, 5, action.call_id)
    assert g.review(action, score=low) is Decision.APPROVED
    assert g.audit[-1].reason == "low-risk" and g.audit[-1].review_attempts == 0
    print("1. matching low-risk evidence -> fast approval")

    stale = Score(0.01, 5, action.call_id, lag=4)
    assert g.review(action, score=stale, synchronous_answers=('{"outcome":"allow"}',)) is Decision.APPROVED
    assert g.audit[-1].review_attempts == 1
    print("2. stale score -> synchronous review; not automatic allow")

    changed = Score(0.01, 4, action.call_id)
    assert g.review(action, score=changed, synchronous_answers=('{"outcome":"deny"}',)) is Decision.DENIED
    assert g.audit[-1].reason == "synchronous-deny"
    print("3. authorization change -> fresh review can deny")

    wrong = Score(0.02, 5, "older-tool-call")
    assert g.review(action, score=wrong) is Decision.ASK_USER
    assert g.audit[-1].reason == "action-not-covered"
    print("4. old call-specific score cannot authorize another action")

    assert g.review(action, score=Score(0.90, 5, action.call_id)) is Decision.ASK_USER
    assert g.review(action, score=Score(0.10, 5, action.call_id, failed_unscored=True)) is Decision.ASK_USER
    print("5. elevated risk or unscored failure -> cannot fast approve")

    result = g.review(action, score=low, require_fresh=True,
                      synchronous_answers=("transport", '{"outcome":"allow"}'))
    assert result is Decision.APPROVED and g.audit[-1].review_attempts == 2
    assert g.audit[-1].reason == "synchronous-allow"
    print("6. fresh review retries a transient transport error")

    assert g.review(action, require_fresh=True,
                    synchronous_answers=("not valid JSON",)) is Decision.ASK_USER
    assert g.review(action, cancelled=True) is Decision.ABORT
    print("7. malformed output not auto-approved; cancellation aborts")

    human = ToyGuardian(reviewer_mode="user")
    assert human.review(action, score=low) is Decision.ASK_USER
    off = ToyGuardian(policy_mode="disabled")
    assert off.review(action, score=low) is Decision.ASK_USER
    print("8. user-review / disabled Guardian routes outside auto-review")

    assert g.try_execute(action, Decision.APPROVED, sandbox_allowed=False,
                         upstream_allowed=True) == "sandbox-denied"
    assert g.try_execute(action, Decision.APPROVED, sandbox_allowed=True,
                         upstream_allowed=False) == "upstream-data-denied"
    assert g.try_execute(action, Decision.APPROVED, sandbox_allowed=True,
                         upstream_allowed=True) == "executed"
    assert g.executed == ["call-1"]
    print("9. Guardian approval is separate from sandbox and upstream ACL")
    print("All teaching assertions passed")


if __name__ == "__main__":
    main()
