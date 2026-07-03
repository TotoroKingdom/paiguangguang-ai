import { PageShell } from "@/components/page-shell";

export default function OfficeAgentPage() {
  return (
    <PageShell
      eyebrow="V3 Module Placeholder"
      title="Office Agent"
      description="This route is reserved for mock office automation workflows that show tool calls and structured outputs."
      status="Tool Focus"
    >
      <div className="border-l-4 border-brass bg-paper px-4 py-3">Task planning and tool selection</div>
      <div className="border-l-4 border-tide bg-paper px-4 py-3">Step-by-step execution log</div>
      <div className="border-l-4 border-clay bg-paper px-4 py-3">Structured output and summary</div>
    </PageShell>
  );
}
