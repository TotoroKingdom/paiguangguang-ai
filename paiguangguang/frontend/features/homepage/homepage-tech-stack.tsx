import Image from "next/image";

import type { HomepageTech } from "./homepage-data";
import { techStack } from "./homepage-data";

const categoryLabels: Record<HomepageTech["category"], string> = {
  frontend: "Frontend",
  backend: "Backend",
  ai: "AI",
  storage: "Storage",
  delivery: "Delivery"
};

export function HomepageTechStack() {
  return (
    <section className="space-y-5">
      <div>
        <p className="text-sm font-semibold uppercase tracking-normal text-clay">Stack</p>
        <h2 className="mt-2 text-3xl font-semibold text-ink">Built with production-oriented AI tooling</h2>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        {techStack.map((item) => (
          <div key={`${item.category}-${item.name}`} className="border border-ink/10 bg-white/65 p-4">
            <p className="text-xs font-semibold uppercase text-moss">{categoryLabels[item.category]}</p>
            <div className="mt-3 flex items-center gap-3">
              {item.imageSrc ? (
                <div className="relative h-10 w-10 shrink-0 overflow-hidden border border-ink/10 bg-paper">
                  <Image src={item.imageSrc} alt={item.name} fill className="object-contain p-1" />
                </div>
              ) : null}
              <p className="text-base font-semibold text-ink">{item.name}</p>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
