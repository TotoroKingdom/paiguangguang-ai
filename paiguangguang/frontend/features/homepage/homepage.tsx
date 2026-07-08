import { PortfolioChatPanel } from "@/features/portfolio-chat/portfolio-chat-panel";

import { HomepageHero } from "./homepage-hero";
import { HomepageModuleLinks } from "./homepage-module-links";
import { HomepageProjects } from "./homepage-projects";
import { HomepageTechStack } from "./homepage-tech-stack";
import { HomepageWorkflow } from "./homepage-workflow";

export function Homepage() {
  return (
    <div className="space-y-12">
      <HomepageHero />
      <section id="portfolio-chat" className="scroll-mt-24">
        <PortfolioChatPanel />
      </section>
      <HomepageWorkflow />
      <HomepageModuleLinks />
      <HomepageProjects />
      <HomepageTechStack />
    </div>
  );
}
