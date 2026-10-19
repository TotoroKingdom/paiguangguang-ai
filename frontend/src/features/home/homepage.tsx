import { AICoreExperience } from "@/components/three/ai-core-experience";
import { homepageContact, homepageSections } from "./homepage-data";
import { HomepageContact } from "./homepage-contact";
import { HomepageHero } from "./homepage-hero";
import { HomepageOverview } from "./homepage-overview";
import { HomepageBuilding, HomepageExploring, HomepageProjects } from "./homepage-projects";
import { HomepageRoadmap } from "./homepage-roadmap";
import { HomePageFrame } from "./home-page-frame";

export function Homepage() {
  return (
    <HomePageFrame
      activePage="home"
      footerCopy={homepageContact.footerCopy}
      overlay={<AICoreExperience />}
    >
      <HomepageHero />
        <section id="capabilities" className="brand-section brand-systems" aria-labelledby="capabilities-title">
          <div className="brand-section-heading">
            <div className="brand-section-heading__copy">
              <h2 id="capabilities-title" className="brand-section-title">{homepageSections.capabilities.title}</h2>
              <p className="brand-section-description">{homepageSections.capabilities.description}</p>
            </div>
            <div className="brand-section-visual" aria-hidden="true">
              <span className="ai-scene-anchor" data-ai-scene-anchor="capabilities" />
            </div>
          </div>
        <HomepageOverview />
      </section>
      <HomepageProjects />
      <HomepageBuilding />
      <HomepageExploring />
      <HomepageRoadmap />
      <HomepageContact />
    </HomePageFrame>
  );
}
