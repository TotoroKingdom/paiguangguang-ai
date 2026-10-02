import { HomepageContact } from "./homepage-contact";
import { HomepageHero } from "./homepage-hero";
import { HomepageOverview } from "./homepage-overview";
import { HomepageBuilding, HomepageExploring, HomepageProjects } from "./homepage-projects";
import { HomepageRoadmap } from "./homepage-roadmap";
import { HomePageFrame } from "./home-page-frame";

export function Homepage() {
  return (
    <HomePageFrame activePage="home">
      <HomepageHero />
      <section id="capabilities" className="brand-section brand-systems" aria-labelledby="capabilities-title">
        <div className="brand-section-heading">
          <p className="brand-eyebrow">02 / 工程能力</p>
          <div>
            <h2 id="capabilities-title" className="brand-section-title">我能构建什么</h2>
            <p className="brand-section-description">从知识检索、智能体执行，到支撑产品交付的应用与基础设施。</p>
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
