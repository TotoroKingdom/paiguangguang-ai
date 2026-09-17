import { HomepageContact } from "./homepage-contact";
import { HomepageHero } from "./homepage-hero";
import { HomepageOverview } from "./homepage-overview";
import { HomepageProjects } from "./homepage-projects";
import { HomepageRoadmap } from "./homepage-roadmap";
import { HomepageTechStack } from "./homepage-tech-stack";
import { HomePageFrame } from "./home-page-frame";
import { HomepageRagEntry } from "./homepage-rag-entry";

function SectionHeading() {
  return (
    <div className="section-intro section-intro--center">
      <p className="eyebrow">Retrieval · Reasoning · Delivery</p>
      <h2 className="section-title">把复杂的 AI，做成简单的体验</h2>
      <p className="section-description">
        从知识入库到 Agent 执行，把模型能力收束成稳定、可观测、能真正落地的产品体验。
      </p>
    </div>
  );
}

export function Homepage() {
  return (
    <HomePageFrame activePage="home">
      <HomepageHero />

      <section id="overview" className="home-section home-section--overview scroll-mt-24">
        <SectionHeading />
        <HomepageOverview />
      </section>

      <HomepageTechStack />
      <HomepageRagEntry />
      <HomepageProjects />
      <HomepageRoadmap />
      <HomepageContact />
    </HomePageFrame>
  );
}
