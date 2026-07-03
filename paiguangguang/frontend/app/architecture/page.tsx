import { PageShell } from "@/components/page-shell";

export default function ArchitecturePage() {
  return (
    <PageShell
      eyebrow="V2 Module Placeholder"
      title="Architecture Visualization"
      description="This route is reserved for the React Flow system graph covering the frontend, backend, AI layer, and storage."
      status="System Focus"
    >
      <div className="border-l-4 border-brass bg-paper px-4 py-3">Frontend, backend, and AI layer map</div>
      <div className="border-l-4 border-tide bg-paper px-4 py-3">Interactive node and detail panel area</div>
      <div className="border-l-4 border-clay bg-paper px-4 py-3">Workflow and data-flow legend</div>
    </PageShell>
  );
}
