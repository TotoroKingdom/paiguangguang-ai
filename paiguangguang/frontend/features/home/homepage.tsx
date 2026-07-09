import { HomepageContact } from "./homepage-contact";
import { HomepageHero } from "./homepage-hero";
import { HomepageOverview } from "./homepage-overview";
import { HomepageProjects } from "./homepage-projects";
import { HomepageRoadmap } from "./homepage-roadmap";
import { HomepageTechStack } from "./homepage-tech-stack";

export function Homepage() {
  return (
    <div className="relative isolate w-full overflow-hidden bg-[#050816] text-white">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(56,189,248,0.18),transparent_28%),radial-gradient(circle_at_top_right,rgba(217,70,239,0.16),transparent_26%),radial-gradient(circle_at_bottom,rgba(14,165,233,0.12),transparent_22%)]" />
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.04)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.04)_1px,transparent_1px)] bg-[size:38px_38px] opacity-[0.06]" />
      <div className="relative flex w-full flex-col gap-20 py-6 sm:py-8 lg:py-10">
        <HomepageHero />
        <HomepageOverview />
        <HomepageTechStack />
        <HomepageProjects />
        <HomepageRoadmap />
        <HomepageContact />
      </div>
    </div>
  );
}
