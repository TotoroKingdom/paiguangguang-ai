import { PageShell } from "@/components/page-shell";

export default function KnowledgeAgentPage() {
  return (
    <PageShell
      eyebrow="V2 Module Placeholder"
      title="Knowledge Agent"
      description="This route is reserved for the enterprise RAG demo with document ingestion, retrieval, answers, and citations."
      status="Layout Focus"
    >
      <div className="border-l-4 border-brass bg-paper px-4 py-3">Document upload and ingestion area</div>
      <div className="border-l-4 border-tide bg-paper px-4 py-3">Question and answer workspace</div>
      <div className="border-l-4 border-clay bg-paper px-4 py-3">Sources and citation rail</div>
    </PageShell>
  );
}
