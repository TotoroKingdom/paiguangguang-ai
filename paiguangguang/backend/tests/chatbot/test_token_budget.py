from __future__ import annotations

from app.chatbot.llm.token_estimator import ApproxTokenEstimator


def test_token_estimator_counts_text_and_messages_with_stable_boundaries() -> None:
    estimator = ApproxTokenEstimator()

    assert estimator.estimate_text("") == 0
    assert estimator.estimate_text("abcd") == 1
    assert estimator.estimate_text("abcde") == 2
    assert estimator.estimate_message("abcd") > estimator.estimate_text("abcd")
