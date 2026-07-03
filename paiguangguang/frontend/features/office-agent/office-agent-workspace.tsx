"use client";

import { FormEvent, useState } from "react";

import { ApiError } from "@/lib/api";
import { runOfficeAgent } from "@/lib/office-agent";
import type { OfficeAgentFinalOutputData, OfficeAgentStepData, OfficeWorkflow } from "@/types/office-agent";

const workflowOptions: Array<{
  value: OfficeWorkflow;
  label: string;
  description: string;
}> = [
  {
    value: "generate_report",
    label: "Generate Report",
    description: "Builds a structured report artifact with sections and recommendations.",
  },
  {
    value: "summarize_data",
    label: "Summarize Data",
    description: "Produces a concise summary artifact with key points.",
  },
  {
    value: "write_email",
    label: "Write Email",
    description: "Creates a structured email draft ready to send as a final artifact.",
  },
] as const;

const starterPrompt = "Create a project status report for the AI portfolio progress update.";

function badgeClass(kind: OfficeAgentStepData["kind"]) {
  if (kind === "plan") return "border-brass/30 bg-brass/10 text-ink";
  if (kind === "tool_call") return "border-tide/30 bg-tide/10 text-ink";
  if (kind === "observation") return "border-clay/30 bg-clay/10 text-ink";
  return "border-moss/30 bg-moss/10 text-ink";
}

function kindLabel(kind: OfficeAgentStepData["kind"]) {
  if (kind === "tool_call") return "Tool";
  if (kind === "observation") return "Observation";
  if (kind === "synthesis") return "Synthesis";
  return "Plan";
}

function formatData(value: Record<string, unknown>) {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function StepCard({ step }: { step: OfficeAgentStepData }) {
  return (
    <li className="rounded-2xl border border-ink/10 bg-white/70 p-4 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-ink">{step.title}</p>
          <p className="mt-1 text-xs uppercase tracking-[0.2em] text-ink/55">{step.step_id}</p>
        </div>
        <span className={["rounded-full border px-3 py-1 text-xs font-semibold", badgeClass(step.kind)].join(" ")}>
          {kindLabel(step.kind)}
        </span>
      </div>
      <p className="mt-3 text-sm leading-7 text-ink/75">{step.detail}</p>
      <pre className="mt-4 overflow-x-auto rounded-xl border border-ink/10 bg-paper/80 p-3 text-xs leading-6 text-ink/75">
        {formatData(step.data)}
      </pre>
    </li>
  );
}

function outputLabel(artifactType: OfficeAgentFinalOutputData["artifact_type"]) {
  if (artifactType === "report") return "Report";
  if (artifactType === "email") return "Email";
  return "Summary";
}

export function OfficeAgentWorkspace() {
  const [workflow, setWorkflow] = useState<OfficeWorkflow>("generate_report");
  const [prompt, setPrompt] = useState(starterPrompt);
  const [steps, setSteps] = useState<OfficeAgentStepData[] | null>(null);
  const [finalOutput, setFinalOutput] = useState<OfficeAgentFinalOutputData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const trimmedPrompt = prompt.trim();
    if (!trimmedPrompt || isLoading) {
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const data = await runOfficeAgent({
        workflow,
        prompt: trimmedPrompt,
      });
      setSteps(data.steps);
      setFinalOutput(data.final_output);
    } catch (caughtError) {
      const message = caughtError instanceof ApiError ? caughtError.message : "Unable to run the office agent.";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <section className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
      <div className="space-y-6">
        <section className="border border-ink/10 bg-white/72 p-5 shadow-sm">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-sm font-semibold uppercase tracking-wide text-clay">Office Automation</p>
              <h2 className="mt-2 text-2xl font-semibold text-ink">Mock tool workflow</h2>
              <p className="mt-2 max-w-xl text-sm leading-7 text-ink/70">
                Pick a workflow, provide a prompt, and inspect the visible tool calls that create the final office
                artifact.
              </p>
            </div>
            <div className="rounded-full border border-ink/10 bg-paper px-3 py-1 text-xs font-semibold text-ink/65">
              {isLoading ? "Running" : "Ready"}
            </div>
          </div>

          <form onSubmit={handleSubmit} className="mt-5 space-y-4">
            <label className="block">
              <span className="mb-2 block text-sm font-semibold text-ink">Workflow</span>
              <select
                value={workflow}
                onChange={(event) => setWorkflow(event.target.value as OfficeWorkflow)}
                className="w-full border border-ink/15 bg-white px-4 py-3 text-sm text-ink outline-none transition focus:border-tide/50 focus:ring-2 focus:ring-tide/10"
              >
                {workflowOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
              <span className="mt-2 block text-xs leading-5 text-ink/55">
                {workflowOptions.find((option) => option.value === workflow)?.description}
              </span>
            </label>

            <label className="block">
              <span className="mb-2 block text-sm font-semibold text-ink">Prompt</span>
              <textarea
                value={prompt}
                onChange={(event) => setPrompt(event.target.value)}
                rows={6}
                placeholder="Describe the office task you want the mock workflow to perform."
                className="w-full resize-none border border-ink/15 bg-white px-4 py-3 text-sm leading-7 text-ink outline-none transition placeholder:text-ink/40 focus:border-tide/50 focus:ring-2 focus:ring-tide/10"
              />
            </label>

            <div className="rounded-2xl border border-dashed border-ink/15 bg-paper/70 px-4 py-3 text-sm leading-7 text-ink/65">
              The mock office tools never mutate files. They only return structured artifacts that are easy to inspect.
            </div>

            {error ? (
              <div className="border border-clay/25 bg-clay/10 px-4 py-3 text-sm leading-7 text-ink">{error}</div>
            ) : null}

            <div className="flex flex-wrap gap-3">
              <button
                type="submit"
                disabled={isLoading}
                className="border border-tide/40 bg-tide px-4 py-2.5 text-sm font-semibold text-paper transition hover:bg-tide/90 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isLoading ? "Running..." : "Run workflow"}
              </button>
              <button
                type="button"
                onClick={() => {
                  setSteps(null);
                  setFinalOutput(null);
                }}
                className="border border-ink/15 bg-white px-4 py-2.5 text-sm font-semibold text-ink transition hover:border-ink/25 hover:bg-paper"
              >
                Clear result
              </button>
            </div>
          </form>
        </section>

        <section className="border border-ink/10 bg-white/72 p-5 shadow-sm">
          <p className="text-sm font-semibold uppercase tracking-wide text-clay">Execution Steps</p>
          {steps ? (
            <ul className="mt-4 space-y-3">
              {steps.map((step) => (
                <StepCard key={step.step_id} step={step} />
              ))}
            </ul>
          ) : (
            <div className="mt-4 rounded-2xl border border-dashed border-ink/15 bg-paper/70 p-5 text-sm leading-7 text-ink/60">
              Run the office workflow to reveal the plan, mock tool calls, observations, and synthesis.
            </div>
          )}
        </section>
      </div>

      <aside className="space-y-6">
        <section className="border border-ink/10 bg-white/72 p-5 shadow-sm">
          <p className="text-sm font-semibold uppercase tracking-wide text-clay">Final Result</p>
          <div className="mt-4 rounded-2xl border border-ink/10 bg-paper/80 p-4">
            {finalOutput ? (
              <div className="space-y-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wide text-clay">
                      {outputLabel(finalOutput.artifact_type)}
                    </p>
                    <h3 className="mt-1 text-xl font-semibold text-ink">{finalOutput.title}</h3>
                  </div>
                  <span className="rounded-full border border-ink/10 bg-white/70 px-3 py-1 text-xs font-semibold text-ink/70">
                    {finalOutput.artifact_type}
                  </span>
                </div>
                <p className="text-sm leading-7 text-ink/75">{finalOutput.summary}</p>
                <pre className="overflow-x-auto whitespace-pre-wrap rounded-xl border border-ink/10 bg-white px-3 py-3 text-xs leading-6 text-ink/75">
                  {finalOutput.content}
                </pre>
              </div>
            ) : (
              <p className="text-sm leading-7 text-ink/60">
                The structured office artifact appears here after the workflow completes.
              </p>
            )}
          </div>
        </section>

        <section className="border border-ink/10 bg-white/72 p-5 shadow-sm">
          <p className="text-sm font-semibold uppercase tracking-wide text-clay">Artifact Metadata</p>
          {finalOutput ? (
            <pre className="mt-4 overflow-x-auto rounded-2xl border border-ink/10 bg-paper/80 p-4 text-xs leading-6 text-ink/75">
              {formatData(finalOutput.metadata)}
            </pre>
          ) : (
            <div className="mt-4 rounded-2xl border border-dashed border-ink/15 bg-paper/70 p-5 text-sm leading-7 text-ink/60">
              Metadata such as keywords or recipient information will appear here.
            </div>
          )}
        </section>
      </aside>
    </section>
  );
}
