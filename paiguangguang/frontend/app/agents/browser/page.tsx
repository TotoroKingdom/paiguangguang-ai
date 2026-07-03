import { PageShell } from "@/components/page-shell";

export default function BrowserAgentPage() {
  return (
    <PageShell
      eyebrow="V3 Module Placeholder"
      title="Browser Agent"
      description="This route is reserved for the mock web research workflow with planning, search steps, intermediate results, and a final answer."
      status="Workflow Focus"
    >
      <div className="border-l-4 border-brass bg-paper px-4 py-3">Planning and intent capture zone</div>
      <div className="border-l-4 border-tide bg-paper px-4 py-3">Search trace and intermediate results</div>
      <div className="border-l-4 border-clay bg-paper px-4 py-3">Final synthesis and response panel</div>
    </PageShell>
  );
}
