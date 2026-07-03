import { PageShell } from "@/components/page-shell";
import { BrowserAgentWorkspace } from "@/features/browser-agent/browser-agent-workspace";

export default function BrowserAgentPage() {
  return (
    <div className="space-y-8">
      <PageShell
        eyebrow="V3 Live Module"
        title="Browser Agent"
        description="Run a mock research workflow that shows the plan, search steps, intermediate results, and final answer."
        status="Research Workflow"
      >
        <div className="border-l-4 border-brass bg-paper px-4 py-3">
          The workflow remains visible from prompt to synthesis.
        </div>
        <div className="border-l-4 border-tide bg-paper px-4 py-3">
          Search results are deterministic so the demo is easy to inspect and test.
        </div>
        <div className="border-l-4 border-clay bg-paper px-4 py-3">
          The layout stays readable on desktop and mobile.
        </div>
      </PageShell>

      <BrowserAgentWorkspace />
    </div>
  );
}
