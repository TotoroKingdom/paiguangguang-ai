from __future__ import annotations

from evals import load_rag_eval_dataset
from evals.rag_eval_dataset import get_rag_eval_dataset_path


def test_rag_eval_dataset_loads_from_repository() -> None:
    dataset = load_rag_eval_dataset()

    assert get_rag_eval_dataset_path().exists()
    assert dataset["version"] == 1
    assert len(dataset["corpus"]) == 3
    assert len(dataset["cases"]) == 3


def test_rag_eval_dataset_cases_include_retrieval_and_answer_expectations() -> None:
    dataset = load_rag_eval_dataset()

    for case in dataset["cases"]:
        assert case["id"]
        assert case["question"]
        assert case["expected_documents"]
        assert case["expected_chunks"]
        assert case["expected_pages"]
        assert case["answer_notes"]
        citations = case["citation_expectations"]
        assert "must_include_doc_ids" in citations
        assert "must_include_chunk_ids" in citations


def test_rag_eval_dataset_corpus_is_small_and_permission_aware() -> None:
    dataset = load_rag_eval_dataset()

    corpus_by_id = {item["doc_id"]: item for item in dataset["corpus"]}
    assert corpus_by_id["doc-alpha-deploy"]["permission_scope"] == "workspace"
    assert corpus_by_id["doc-secret-runbook"]["permission_scope"] == "admin"
    assert any(
        chunk["metadata"]["workspace_id"] == "workspace-alpha"
        for item in dataset["corpus"]
        for chunk in item["chunks"]
    )
