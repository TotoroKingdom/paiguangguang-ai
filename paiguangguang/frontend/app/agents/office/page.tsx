import { PageShell } from "@/components/page-shell";
import { OfficeAgentWorkspace } from "@/features/office-agent/office-agent-workspace";

export default function OfficeAgentPage() {
  return (
    <div className="space-y-8">
      <PageShell
        eyebrow="V3 Live Module"
        title="Office Agent"
        description="Run mock office automation workflows that show tool calls, execution steps, and structured outputs."
        status="Tool Workflow"
      >
        <div className="border-l-4 border-brass bg-paper px-4 py-3">
          The workflow shows the full path from input to artifact.
        </div>
        <div className="border-l-4 border-tide bg-paper px-4 py-3">
          Supported mock tools are generate report, summarize data, and write email.
        </div>
        <div className="border-l-4 border-clay bg-paper px-4 py-3">
          No files are modified and no Office software is required.
        </div>
      </PageShell>

      <OfficeAgentWorkspace />
    </div>
  );
}
