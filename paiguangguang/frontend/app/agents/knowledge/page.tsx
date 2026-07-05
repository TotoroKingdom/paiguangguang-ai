import { PageShell } from "@/components/page-shell";
import { KnowledgeAgentShell } from "@/features/knowledge-agent/knowledge-agent-shell";

export default function KnowledgeAgentPage() {
  return (
    <div className="space-y-8">
      <PageShell
        eyebrow="V2 Live Module"
        title="Knowledge Agent"
        description="Upload or paste reference text, index it into Chroma, and ask questions with visible sources and citations."
        status="RAG Workspace"
      >
        <div className="border-l-4 border-brass bg-paper px-4 py-3">
          Ingest text from a file or paste area into the retrieval collection.
        </div>
        <div className="border-l-4 border-tide bg-paper px-4 py-3">
          Query the backend for answers grounded in retrieved chunks.
        </div>
        <div className="border-l-4 border-clay bg-paper px-4 py-3">
          Review doc IDs, chunk IDs, and scores in the citation rail.
        </div>
      </PageShell>

      <KnowledgeAgentShell />
    </div>
  );
}
