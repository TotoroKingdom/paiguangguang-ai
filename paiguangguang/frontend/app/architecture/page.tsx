import { PageShell } from "@/components/page-shell";
import { ArchitectureGraphWorkspace } from "@/features/architecture-flow/architecture-graph-workspace";

export default function ArchitecturePage() {
  return (
    <div className="space-y-8">
      <PageShell
        eyebrow="V2 Live Module"
        title="Architecture Visualization"
        description="Explore the system graph that connects the frontend surfaces, backend services, AI layer, and storage components."
        status="System Map"
      >
        <div className="border-l-4 border-brass bg-paper px-4 py-3">
          A stable graph returned by the backend API powers this visualization.
        </div>
        <div className="border-l-4 border-tide bg-paper px-4 py-3">
          Node clicks open a details rail that explains each system component.
        </div>
        <div className="border-l-4 border-clay bg-paper px-4 py-3">
          The layout is tuned for both desktop canvases and mobile stacked reading.
        </div>
      </PageShell>

      <ArchitectureGraphWorkspace />
    </div>
  );
}
