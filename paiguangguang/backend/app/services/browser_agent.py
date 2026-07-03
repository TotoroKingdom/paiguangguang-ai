from __future__ import annotations

import re

from app.schemas.browser import (
    BrowserAgentRequest,
    BrowserAgentRunData,
    BrowserAgentStepData,
    BrowserSearchResultData,
)
from app.services.task_service import TaskService, get_task_service
from app.tools.browser_search import MockBrowserSearchResult, MockBrowserSearchTool


def _extract_keywords(prompt: str) -> list[str]:
    stopwords = {
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

    keywords: list[str] = []
    seen: set[str] = set()
    for token in re.findall(r"[a-z0-9]+", prompt.lower()):
        if len(token) < 3 or token in stopwords or token in seen:
            continue
        seen.add(token)
        keywords.append(token)
    return keywords


def _build_search_query(prompt: str) -> str:
    keywords = _extract_keywords(prompt)
    if keywords:
        return " ".join(keywords[:6])
    return prompt.strip()


def _build_plan(prompt: str, search_query: str) -> list[BrowserAgentStepData]:
    keywords = _extract_keywords(prompt)
    return [
        BrowserAgentStepData(
            step_id="step-1",
            kind="plan",
            title="Create research plan",
            detail="Identify the research focus and derive stable search terms from the prompt.",
            data={
                "prompt": prompt,
                "keywords": keywords,
            },
        ),
        BrowserAgentStepData(
            step_id="step-2",
            kind="plan",
            title="Run mock browser search",
            detail="Query the deterministic mock search corpus and capture the ranked results.",
            data={
                "search_query": search_query,
                "tool": "mock_browser_search",
            },
        ),
        BrowserAgentStepData(
            step_id="step-3",
            kind="plan",
            title="Synthesize answer",
            detail="Combine the strongest matches into a concise answer with visible evidence.",
            data={
                "citation_style": "inline mock references",
            },
        ),
    ]


class BrowserAgentService:
    def __init__(
        self,
        search_tool: MockBrowserSearchTool | None = None,
        task_service: TaskService | None = None,
    ) -> None:
        self.search_tool = search_tool or MockBrowserSearchTool()
        self.task_service = task_service or get_task_service()

    def run(self, request: BrowserAgentRequest) -> BrowserAgentRunData:
        prompt = request.prompt.strip()
        search_query = _build_search_query(prompt)
        task_id = self.task_service.start_task(
            task_type="browser_agent",
            title="Browser research workflow",
            metadata={
                "prompt": prompt,
                "top_k": request.top_k,
            },
        )

        try:
            plan_steps = _build_plan(prompt, search_query)
            search_results = self.search_tool.search(search_query, top_k=request.top_k)

            steps = [
                *plan_steps,
                BrowserAgentStepData(
                    step_id="step-4",
                    kind="tool_call",
                    title="Call mock search tool",
                    detail="Execute the deterministic browser search simulation.",
                    data={
                        "tool": "mock_browser_search",
                        "query": search_query,
                        "top_k": request.top_k,
                    },
                ),
                BrowserAgentStepData(
                    step_id="step-5",
                    kind="observation",
                    title="Review intermediate results",
                    detail="Inspect the top-ranked mock results and extract evidence for synthesis.",
                    data={
                        "results": [
                            BrowserSearchResultData(
                                title=result.title,
                                url=result.url,
                                snippet=result.snippet,
                                score=result.score,
                            ).model_dump()
                            for result in search_results
                        ],
                    },
                ),
                BrowserAgentStepData(
                    step_id="step-6",
                    kind="synthesis",
                    title="Write final answer",
                    detail="Assemble a final response grounded in the strongest mock references.",
                    data={
                        "evidence": [
                            {
                                "title": result.title,
                                "url": result.url,
                                "score": result.score,
                            }
                            for result in search_results
                        ]
                    },
                ),
            ]

            for index, step in enumerate(steps, start=1):
                self.task_service.record_step(task_id, step=step.model_dump(mode="json"), index=index, total=len(steps))

            final_answer = self._synthesize_answer(prompt, search_query, search_results)
            result = BrowserAgentRunData(
                prompt=prompt,
                search_query=search_query,
                steps=steps,
                search_results=[
                    BrowserSearchResultData(
                        title=result.title,
                        url=result.url,
                        snippet=result.snippet,
                        score=result.score,
                    )
                    for result in search_results
                ],
                final_answer=final_answer,
                task_id=task_id,
            )
            self.task_service.complete_task(task_id, output=result.model_dump(mode="json"))
            return result
        except Exception as exc:
            self.task_service.fail_task(
                task_id,
                message="Browser workflow failed",
                error=str(exc),
                payload={
                    "prompt": prompt,
                    "search_query": search_query,
                },
            )
            raise

    @staticmethod
    def _synthesize_answer(
        prompt: str,
        search_query: str,
        results: list[MockBrowserSearchResult],
    ) -> str:
        if not results:
            return (
                f"I reviewed the mock browser workflow for: {prompt}. "
                f"The search query was '{search_query}', but no relevant mock results were returned."
            )

        top_result = results[0]
        supporting_titles = [result.title for result in results[1:3]]
        lines = [
            f"I reviewed the mock browser workflow for: {prompt}.",
            f"The search query was '{search_query}'.",
            f"The strongest match is '{top_result.title}', which suggests: {top_result.snippet}",
        ]
        if supporting_titles:
            lines.append(f"Supporting references include {', '.join(supporting_titles)}.")
        lines.append("Recommended next step: refine the prompt or continue with another mock search pass.")
        return " ".join(lines)


_BROWSER_AGENT_SERVICE = BrowserAgentService()


def get_browser_agent_service() -> BrowserAgentService:
    return _BROWSER_AGENT_SERVICE
