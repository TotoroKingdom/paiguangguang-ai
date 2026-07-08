import { workflowSteps } from "./homepage-data";

export function HomepageWorkflow() {
  return (
    <section className="space-y-5">
      <div>
        <p className="text-sm font-semibold uppercase tracking-normal text-clay">Workflow visibility</p>
        <h2 className="mt-2 text-3xl font-semibold text-ink">Every AI surface shows how the answer is made</h2>
      </div>
      <div className="grid gap-4 md:grid-cols-4">
        {workflowSteps.map((step) => (
          <div key={step.label} className="border border-ink/10 bg-white/65 p-5">
            <p className="text-sm font-semibold text-brass">{step.label}</p>
            <h3 className="mt-3 text-lg font-semibold text-ink">{step.title}</h3>
            <p className="mt-3 text-sm leading-7 text-ink/70">{step.description}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
