from __future__ import annotations

from app.schemas.office import (
    OfficeAgentFinalOutputData,
    OfficeAgentRequest,
    OfficeAgentRunData,
    OfficeAgentStepData,
)
from app.tools.office_tools import (
    _append_suffix_once,
    generate_report,
    summarize_data,
    write_email,
)

SUPPORTED_WORKFLOWS = {"generate_report", "summarize_data", "write_email"}


def _normalize_workflow(workflow: str) -> str:
    return workflow.strip().lower().replace("-", "_").replace(" ", "_")


def _build_plan(prompt: str, workflow: str) -> list[OfficeAgentStepData]:
    return [
        OfficeAgentStepData(
            step_id="step-1",
            kind="plan",
            title="Define office workflow",
            detail="Translate the user request into a structured office automation workflow.",
            data={
                "prompt": prompt,
                "workflow": workflow,
            },
        ),
        OfficeAgentStepData(
            step_id="step-2",
            kind="plan",
            title="Summarize request context",
            detail="Create a deterministic summary that can feed the downstream mock tools.",
            data={
                "tool": "summarize_data",
            },
        ),
    ]


class OfficeAgentService:
    def run(self, request: OfficeAgentRequest) -> OfficeAgentRunData:
        prompt = request.prompt.strip()
        workflow = _normalize_workflow(request.workflow)

        if workflow not in SUPPORTED_WORKFLOWS:
            raise ValueError(f"Unsupported office workflow: {request.workflow}")

        summary = summarize_data(prompt)
        plan_steps = _build_plan(prompt, workflow)

        if workflow == "summarize_data":
            tool_steps = [
                OfficeAgentStepData(
                    step_id="step-3",
                    kind="tool_call",
                    title="Call summarize_data",
                    detail="Generate a deterministic summary of the request.",
                    data={"tool": "summarize_data", "input": prompt},
                ),
                OfficeAgentStepData(
                    step_id="step-4",
                    kind="observation",
                    title="Review summary output",
                    detail="Inspect the generated summary and key points.",
                    data={
                        "summary": summary["summary"],
                        "key_points": summary["key_points"],
                        "keywords": summary["keywords"],
                    },
                ),
                OfficeAgentStepData(
                    step_id="step-5",
                    kind="synthesis",
                    title="Finalize summary artifact",
                    detail="Package the summary into a structured office result.",
                    data={"artifact_type": "summary"},
                ),
            ]
            final_output = OfficeAgentFinalOutputData(
                artifact_type="summary",
                title=_append_suffix_once(str(summary["subject"]), "Summary"),
                summary=str(summary["summary"]),
                content="\n".join(f"- {point}" for point in summary["key_points"]),
                metadata={
                    "keywords": summary["keywords"],
                    "key_points": summary["key_points"],
                },
            )
            return OfficeAgentRunData(
                workflow=workflow,
                prompt=prompt,
                steps=[*plan_steps, *tool_steps],
                final_output=final_output,
            )

        if workflow == "generate_report":
            report = generate_report(prompt, summary)
            tool_steps = [
                OfficeAgentStepData(
                    step_id="step-3",
                    kind="tool_call",
                    title="Call summarize_data",
                    detail="Generate the supporting summary for the report.",
                    data={"tool": "summarize_data", "input": prompt},
                ),
                OfficeAgentStepData(
                    step_id="step-4",
                    kind="observation",
                    title="Review summary output",
                    detail="Inspect the summary that will feed the report draft.",
                    data={
                        "summary": summary["summary"],
                        "key_points": summary["key_points"],
                    },
                ),
                OfficeAgentStepData(
                    step_id="step-5",
                    kind="tool_call",
                    title="Call generate_report",
                    detail="Assemble the structured report artifact.",
                    data={"tool": "generate_report", "input": prompt},
                ),
                OfficeAgentStepData(
                    step_id="step-6",
                    kind="observation",
                    title="Review report draft",
                    detail="Check the generated report sections and content.",
                    data={
                        "title": report["title"],
                        "sections": report["sections"],
                    },
                ),
                OfficeAgentStepData(
                    step_id="step-7",
                    kind="synthesis",
                    title="Finalize report artifact",
                    detail="Package the report into a structured office result.",
                    data={"artifact_type": "report"},
                ),
            ]
            final_output = OfficeAgentFinalOutputData(
                artifact_type="report",
                title=str(report["title"]),
                summary=str(report["summary"]),
                content=str(report["content"]),
                metadata={
                    "sections": report["sections"],
                    "keywords": summary["keywords"],
                },
            )
            return OfficeAgentRunData(
                workflow=workflow,
                prompt=prompt,
                steps=[*plan_steps, *tool_steps],
                final_output=final_output,
            )

        email = write_email(prompt, summary)
        tool_steps = [
            OfficeAgentStepData(
                step_id="step-3",
                kind="tool_call",
                title="Call summarize_data",
                detail="Generate the supporting summary for the email draft.",
                data={"tool": "summarize_data", "input": prompt},
            ),
            OfficeAgentStepData(
                step_id="step-4",
                kind="observation",
                title="Review summary output",
                detail="Inspect the summary and keywords before drafting the email.",
                data={
                    "summary": summary["summary"],
                    "key_points": summary["key_points"],
                },
            ),
            OfficeAgentStepData(
                step_id="step-5",
                kind="tool_call",
                title="Call write_email",
                detail="Generate a structured email draft from the summary.",
                data={"tool": "write_email", "input": prompt},
            ),
            OfficeAgentStepData(
                step_id="step-6",
                kind="observation",
                title="Review email draft",
                detail="Check the generated subject and body before finalizing.",
                data={
                    "recipient": email["recipient"],
                    "subject": email["subject"],
                },
            ),
            OfficeAgentStepData(
                step_id="step-7",
                kind="synthesis",
                title="Finalize email artifact",
                detail="Package the email into a structured office result.",
                data={"artifact_type": "email"},
            ),
        ]
        final_output = OfficeAgentFinalOutputData(
            artifact_type="email",
            title=str(email["subject"]),
            summary=str(email["summary"]),
            content=str(email["content"]),
            metadata={
                "recipient": email["recipient"],
                "keywords": summary["keywords"],
            },
        )
        return OfficeAgentRunData(
            workflow=workflow,
            prompt=prompt,
            steps=[*plan_steps, *tool_steps],
            final_output=final_output,
        )


_OFFICE_AGENT_SERVICE = OfficeAgentService()


def get_office_agent_service() -> OfficeAgentService:
    return _OFFICE_AGENT_SERVICE
