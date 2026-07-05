from __future__ import annotations

from evals import load_rag_eval_dataset
from evals.rag_eval_runner import build_mock_query_fn, run_rag_eval_dataset


def test_rag_eval_runner_supports_deterministic_mock_runs() -> None:
    dataset = load_rag_eval_dataset()
    result = run_rag_eval_dataset(build_mock_query_fn(dataset), dataset)

    assert result.total_cases == 3
    assert result.retrieval_hit_rate == 1.0
    assert result.answer_pass_rate == 1.0
    assert result.citation_correctness_rate == 1.0
    assert result.hallucination_flag_rate == 0.0
    assert all(case.retrieval_hit for case in result.cases)
    assert all(case.answer_pass for case in result.cases)
    assert all(case.citation_correct for case in result.cases)
    assert not any(case.hallucination_flag for case in result.cases)


def test_rag_eval_runner_reports_metrics_for_mixed_results() -> None:
    dataset = load_rag_eval_dataset()

    def query_fn(question: str):
        if question == "How is the project deployed?":
            return {
                "answer": "Next.js frontend and FastAPI backend are deployed together.",
                "sources": [
                    {
                        "doc_id": "doc-alpha-deploy",
                        "chunk_id": "doc-alpha-deploy-chunk-0001",
                        "page_number": 1,
                    },
                    {
                        "doc_id": "doc-alpha-deploy",
                        "chunk_id": "doc-alpha-deploy-chunk-0002",
                        "page_number": 1,
                    },
                ],
            }

        if question == "What permission is required to query the knowledge base?":
            return {
                "answer": "The knowledge.query permission is required, and document_admin or system_admin roles satisfy the check.",
                "sources": [
                    {
                        "doc_id": "doc-beta-rbac",
                        "chunk_id": "doc-beta-rbac-chunk-0001",
                        "page_number": 2,
                    }
                ],
            }

        return {
            "answer": "The maintenance note is available.",
            "sources": [
                {
                    "doc_id": "doc-alpha-deploy",
                    "chunk_id": "doc-alpha-deploy-chunk-0001",
                    "page_number": 1,
                }
            ],
        }

    result = run_rag_eval_dataset(query_fn, dataset)

    assert result.total_cases == 3
    assert result.retrieval_hit_rate == 2 / 3
    assert result.answer_pass_rate == 2 / 3
    assert result.citation_correctness_rate == 2 / 3
    assert result.hallucination_flag_rate == 1 / 3

    first, second, third = result.cases
    assert first.retrieval_hit is True
    assert first.answer_pass is True
    assert first.citation_correct is True
    assert first.hallucination_flag is False

    assert second.retrieval_hit is True
    assert second.answer_pass is True
    assert second.citation_correct is True
    assert second.hallucination_flag is False

    assert third.retrieval_hit is False
    assert third.answer_pass is False
    assert third.citation_correct is False
    assert third.hallucination_flag is True
