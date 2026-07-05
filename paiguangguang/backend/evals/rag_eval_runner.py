from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Callable

from .rag_eval_dataset import load_rag_eval_dataset


@dataclass(frozen=True)
class EvalSource:
    doc_id: str
    chunk_id: str
    page_number: int | None = None
    score: float | None = None
    rerank_score: float | None = None
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class EvalCaseResult:
    case_id: str
    question: str
    retrieval_hit: bool
    answer_pass: bool
    citation_correct: bool
    hallucination_flag: bool
    answer: str
    expected_documents: list[str]
    expected_chunks: list[str]
    expected_pages: list[int]
    retrieved_documents: list[str]
    retrieved_chunks: list[str]
    retrieved_pages: list[int]
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class EvalRunResult:
    total_cases: int
    retrieval_hit_rate: float
    answer_pass_rate: float
    citation_correctness_rate: float
    hallucination_flag_rate: float
    cases: list[EvalCaseResult]


def _get_value(item: Any, key: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


def _normalize_int_list(values: Iterable[Any]) -> list[int]:
    normalized: list[int] = []
    for value in values:
        if isinstance(value, int):
            normalized.append(value)
    return normalized


def _normalize_str_list(values: Any) -> list[str]:
    normalized: list[str] = []
    if not isinstance(values, list):
        return normalized
    for value in values:
        if isinstance(value, str) and value.strip():
            normalized.append(value.strip())
    return normalized


def _extract_sources(result: Any) -> list[EvalSource]:
    raw_sources = _get_value(result, "sources", [])
    if not isinstance(raw_sources, list):
        return []

    sources: list[EvalSource] = []
    for item in raw_sources:
        doc_id = _get_value(item, "doc_id")
        chunk_id = _get_value(item, "chunk_id")
        if not isinstance(doc_id, str) or not doc_id.strip():
            continue
        if not isinstance(chunk_id, str) or not chunk_id.strip():
            continue

        metadata = _get_value(item, "metadata", {}) or {}
        sources.append(
            EvalSource(
                doc_id=doc_id.strip(),
                chunk_id=chunk_id.strip(),
                page_number=_get_value(item, "page_number"),
                score=_get_value(item, "score"),
                rerank_score=_get_value(item, "rerank_score"),
                metadata=dict(metadata) if isinstance(metadata, dict) else {},
            )
        )

    return sources


def _extract_answer(result: Any) -> str:
    answer = _get_value(result, "answer", "")
    return answer.strip() if isinstance(answer, str) else ""


def _case_lookup(dataset: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {case["question"]: case for case in dataset.get("cases", []) if isinstance(case, dict)}


def _build_answer(case: dict[str, Any]) -> str:
    keywords = _normalize_str_list(case.get("answer_keywords", []))
    if keywords:
        return " ".join(keywords)
    return case.get("answer_notes", "") or case["question"]


def build_mock_query_fn(dataset: dict[str, Any] | None = None) -> Callable[[str], Any]:
    dataset = dataset or load_rag_eval_dataset()
    cases_by_question = _case_lookup(dataset)
    corpus_by_id = {item["doc_id"]: item for item in dataset.get("corpus", []) if isinstance(item, dict)}

    def query_fn(question: str) -> dict[str, Any]:
        case = cases_by_question.get(question)
        if case is None:
            return {"answer": "", "sources": []}

        sources: list[dict[str, Any]] = []
        citation_expectations = case.get("citation_expectations", {})
        expected_doc_ids = _normalize_str_list(case.get("expected_documents", []))
        expected_chunk_ids = _normalize_str_list(case.get("expected_chunks", []))
        expected_pages = _normalize_int_list(case.get("expected_pages", []))
        candidate_doc_ids = list(
            dict.fromkeys(expected_doc_ids + _normalize_str_list(citation_expectations.get("must_include_doc_ids", [])))
        )

        for doc_id in candidate_doc_ids:
            corpus_doc = corpus_by_id.get(doc_id)
            if corpus_doc is None:
                continue
            for chunk in corpus_doc.get("chunks", []):
                if not isinstance(chunk, dict):
                    continue
                chunk_id = chunk.get("chunk_id")
                if not isinstance(chunk_id, str) or not chunk_id.strip():
                    continue
                if expected_chunk_ids and chunk_id not in expected_chunk_ids and doc_id not in expected_doc_ids:
                    continue
                sources.append(
                    {
                        "doc_id": doc_id,
                        "chunk_id": chunk_id,
                        "title": corpus_doc.get("title"),
                        "page_number": chunk.get("page_number", corpus_doc.get("page_number")),
                        "chunk_index": chunk.get("chunk_index", 0),
                        "text": chunk.get("text", ""),
                        "score": 1.0,
                        "rerank_score": None,
                        "route_scores": {"mock": 1.0},
                        "metadata": dict(chunk.get("metadata", {})),
                    }
                )

        if not sources:
            for doc_id in expected_doc_ids:
                corpus_doc = corpus_by_id.get(doc_id)
                if corpus_doc is None:
                    continue
                for chunk in corpus_doc.get("chunks", []):
                    if not isinstance(chunk, dict):
                        continue
                    chunk_id = chunk.get("chunk_id")
                    if not isinstance(chunk_id, str) or not chunk_id.strip():
                        continue
                    if expected_chunk_ids and chunk_id not in expected_chunk_ids:
                        continue
                    sources.append(
                        {
                            "doc_id": doc_id,
                            "chunk_id": chunk_id,
                            "title": corpus_doc.get("title"),
                            "page_number": chunk.get("page_number", corpus_doc.get("page_number")),
                            "chunk_index": chunk.get("chunk_index", 0),
                            "text": chunk.get("text", ""),
                            "score": 1.0,
                            "rerank_score": None,
                            "route_scores": {"mock": 1.0},
                            "metadata": dict(chunk.get("metadata", {})),
                        }
                    )

        return {
            "answer": _build_answer(case),
            "sources": sources,
            "question": question,
            "pages": expected_pages,
        }

    return query_fn


def _matches_expected(case: dict[str, Any], sources: list[EvalSource]) -> tuple[bool, bool, bool]:
    retrieved_documents = {source.doc_id for source in sources}
    retrieved_chunks = {source.chunk_id for source in sources}
    retrieved_pages = {source.page_number for source in sources if source.page_number is not None}

    expected_documents = set(_normalize_str_list(case.get("expected_documents", [])))
    expected_chunks = set(_normalize_str_list(case.get("expected_chunks", [])))
    expected_pages = set(_normalize_int_list(case.get("expected_pages", [])))

    retrieval_hit = (
        expected_documents.issubset(retrieved_documents)
        and expected_chunks.issubset(retrieved_chunks)
        and expected_pages.issubset(retrieved_pages)
    )

    citation_expectations = case.get("citation_expectations", {})
    must_include_doc_ids = set(_normalize_str_list(citation_expectations.get("must_include_doc_ids", [])))
    must_include_chunk_ids = set(_normalize_str_list(citation_expectations.get("must_include_chunk_ids", [])))
    must_include_pages = set(_normalize_int_list(citation_expectations.get("must_include_pages", [])))
    must_not_include_doc_ids = set(_normalize_str_list(citation_expectations.get("must_not_include_doc_ids", [])))
    must_not_include_chunk_ids = set(_normalize_str_list(citation_expectations.get("must_not_include_chunk_ids", [])))

    citation_correct = (
        must_include_doc_ids.issubset(retrieved_documents)
        and must_include_chunk_ids.issubset(retrieved_chunks)
        and must_include_pages.issubset(retrieved_pages)
        and not must_not_include_doc_ids.intersection(retrieved_documents)
        and not must_not_include_chunk_ids.intersection(retrieved_chunks)
    )

    return retrieval_hit, citation_correct, bool(retrieved_documents or retrieved_chunks or retrieved_pages)


def _answer_pass(case: dict[str, Any], answer: str) -> bool:
    keywords = _normalize_str_list(case.get("answer_keywords", []))
    if not keywords:
        return bool(answer.strip())
    normalized_answer = answer.casefold()
    return all(keyword.casefold() in normalized_answer for keyword in keywords)


def run_rag_eval_dataset(
    query_fn: Callable[[str], Any],
    dataset: dict[str, Any] | None = None,
) -> EvalRunResult:
    dataset = dataset or load_rag_eval_dataset()
    case_results: list[EvalCaseResult] = []

    for case in dataset.get("cases", []):
        if not isinstance(case, dict):
            continue

        raw_result = query_fn(case["question"])
        answer = _extract_answer(raw_result)
        sources = _extract_sources(raw_result)
        retrieval_hit, citation_correct, has_any_sources = _matches_expected(case, sources)
        answer_pass = _answer_pass(case, answer)
        hallucination_flag = not answer_pass or not citation_correct or not has_any_sources

        case_results.append(
            EvalCaseResult(
                case_id=case["id"],
                question=case["question"],
                retrieval_hit=retrieval_hit,
                answer_pass=answer_pass,
                citation_correct=citation_correct,
                hallucination_flag=hallucination_flag,
                answer=answer,
                expected_documents=_normalize_str_list(case.get("expected_documents", [])),
                expected_chunks=_normalize_str_list(case.get("expected_chunks", [])),
                expected_pages=_normalize_int_list(case.get("expected_pages", [])),
                retrieved_documents=[source.doc_id for source in sources],
                retrieved_chunks=[source.chunk_id for source in sources],
                retrieved_pages=[source.page_number for source in sources if source.page_number is not None],
            )
        )

    total_cases = len(case_results)
    if total_cases == 0:
        return EvalRunResult(
            total_cases=0,
            retrieval_hit_rate=0.0,
            answer_pass_rate=0.0,
            citation_correctness_rate=0.0,
            hallucination_flag_rate=0.0,
            cases=[],
        )

    retrieval_hit_rate = sum(1 for result in case_results if result.retrieval_hit) / total_cases
    answer_pass_rate = sum(1 for result in case_results if result.answer_pass) / total_cases
    citation_correctness_rate = sum(1 for result in case_results if result.citation_correct) / total_cases
    hallucination_flag_rate = sum(1 for result in case_results if result.hallucination_flag) / total_cases

    return EvalRunResult(
        total_cases=total_cases,
        retrieval_hit_rate=retrieval_hit_rate,
        answer_pass_rate=answer_pass_rate,
        citation_correctness_rate=citation_correctness_rate,
        hallucination_flag_rate=hallucination_flag_rate,
        cases=case_results,
    )


def _result_to_dict(result: EvalRunResult) -> dict[str, Any]:
    payload = asdict(result)
    payload["cases"] = [asdict(case_result) for case_result in result.cases]
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the local RAG eval dataset.")
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use the built-in deterministic mock query function.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON instead of a human-readable summary.",
    )
    args = parser.parse_args(argv)

    dataset = load_rag_eval_dataset()
    if args.mock:
        query_fn = build_mock_query_fn(dataset)
    else:
        raise SystemExit("Provide --mock for the local runner or import run_rag_eval_dataset() in tests.")

    result = run_rag_eval_dataset(query_fn, dataset)
    if args.json:
        print(json.dumps(_result_to_dict(result), indent=2, sort_keys=True))
        return 0

    print(f"cases: {result.total_cases}")
    print(f"retrieval_hit_rate: {result.retrieval_hit_rate:.2f}")
    print(f"answer_pass_rate: {result.answer_pass_rate:.2f}")
    print(f"citation_correctness_rate: {result.citation_correctness_rate:.2f}")
    print(f"hallucination_flag_rate: {result.hallucination_flag_rate:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
