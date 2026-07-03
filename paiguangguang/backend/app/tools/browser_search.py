from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class MockBrowserSearchResult:
    title: str
    url: str
    snippet: str
    score: float
    matched_terms: list[str]


MOCK_BROWSER_CORPUS = (
    {
        "title": "Mock Browser Research Workflow",
        "url": "https://mock.local/browser-workflow",
        "summary": "Explains how planning, search steps, and synthesis are exposed as visible workflow state.",
        "tags": ("browser", "research", "workflow", "plan", "synthesis"),
    },
    {
        "title": "Portfolio Architecture Overview",
        "url": "https://mock.local/portfolio-architecture",
        "summary": "Describes the frontend, backend, AI, and storage layers used in the portfolio system.",
        "tags": ("portfolio", "architecture", "frontend", "backend", "ai"),
    },
    {
        "title": "RAG and Knowledge Retrieval Notes",
        "url": "https://mock.local/rag-notes",
        "summary": "Covers retrieval, citations, and grounded answers for the knowledge agent module.",
        "tags": ("rag", "retrieval", "knowledge", "citations"),
    },
    {
        "title": "React Flow Visualization Guide",
        "url": "https://mock.local/react-flow-guide",
        "summary": "Shows how interactive node graphs can present system topology and detail panels.",
        "tags": ("react", "flow", "visualization", "graph"),
    },
    {
        "title": "DeepSeek Integration Summary",
        "url": "https://mock.local/deepseek-summary",
        "summary": "Summarizes the chat-completion client and prompt orchestration used by portfolio workflows.",
        "tags": ("deepseek", "chat", "prompt", "llm"),
    },
)


STOPWORDS = {
    "about",
    "after",
    "also",
    "an",
    "and",
    "any",
    "are",
    "be",
    "can",
    "could",
    "did",
    "do",
    "does",
    "done",
    "for",
    "from",
    "get",
    "give",
    "have",
    "how",
    "if",
    "in",
    "into",
    "is",
    "it",
    "its",
    "need",
    "of",
    "on",
    "or",
    "our",
    "should",
    "show",
    "tell",
    "that",
    "the",
    "their",
    "this",
    "to",
    "use",
    "used",
    "using",
    "was",
    "what",
    "when",
    "where",
    "which",
    "with",
    "would",
}


def _tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    seen: set[str] = set()
    result: list[str] = []
    for token in tokens:
        if len(token) < 3 or token in STOPWORDS or token in seen:
            continue
        seen.add(token)
        result.append(token)
    return result


class MockBrowserSearchTool:
    def search(self, query: str, *, top_k: int = 3) -> list[MockBrowserSearchResult]:
        query_terms = _tokenize(query)
        scored_results: list[tuple[float, int, MockBrowserSearchResult]] = []

        for index, page in enumerate(MOCK_BROWSER_CORPUS):
            title_terms = set(_tokenize(page["title"]))
            summary_terms = set(_tokenize(page["summary"]))
            tag_terms = set(page["tags"])
            matched_terms = tuple(
                term for term in query_terms if term in title_terms or term in summary_terms or term in tag_terms
            )

            raw_score = float(len(matched_terms) * 3 + len(title_terms & set(query_terms)) * 2 + len(tag_terms & set(query_terms)))
            snippet = page["summary"]
            if query_terms:
                snippet = f"{page['summary']} Query focus: {', '.join(query_terms[:4])}."

            result = MockBrowserSearchResult(
                title=page["title"],
                url=page["url"],
                snippet=snippet,
                score=0.0,
                matched_terms=list(matched_terms),
            )
            scored_results.append((raw_score, index, result))

        scored_results.sort(key=lambda item: (-item[0], item[1], item[2].title))
        selected = scored_results[:top_k]

        max_score = selected[0][0] if selected else 0.0
        results: list[MockBrowserSearchResult] = []
        for raw_score, _, result in selected:
            score = round(raw_score / max_score, 3) if max_score > 0 else 0.0
            results.append(
                MockBrowserSearchResult(
                    title=result.title,
                    url=result.url,
                    snippet=result.snippet,
                    score=score,
                    matched_terms=list(result.matched_terms),
                )
            )

        return results
