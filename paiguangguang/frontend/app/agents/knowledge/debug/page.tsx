import { PageShell } from "@/components/page-shell";
import { KnowledgeAgentDebugWorkspace } from "@/features/knowledge-agent/knowledge-agent-debug-workspace";

export default function KnowledgeAgentDebugPage() {
  return (
    <div className="space-y-8">
      <PageShell
        eyebrow="V2.3 Debug View"
        title="RAG Debug Page"
        description="Inspect the complete retrieval trace for authorized Knowledge Agent admins and document admins."
        status="Trace Inspector"
      >
        <div className="border-l-4 border-brass bg-paper px-4 py-3">
          Run live debug queries with rewrite, retrieval, fusion, rerank, and citation detail.
        </div>
        <div className="border-l-4 border-tide bg-paper px-4 py-3">
          The page is visible only to authenticated users with admin or document-admin access.
        </div>
        <div className="border-l-4 border-clay bg-paper px-4 py-3">
          Debug queries bypass caches so the trace reflects the live pipeline.
        </div>
      </PageShell>

      <KnowledgeAgentDebugWorkspace />
    </div>
  );
}
