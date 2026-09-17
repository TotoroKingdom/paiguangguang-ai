import { HomepageContact } from "./homepage-contact";
import { HomepageHero } from "./homepage-hero";
import { HomepageOverview } from "./homepage-overview";
import { HomepageProjects } from "./homepage-projects";
import { HomepageRoadmap } from "./homepage-roadmap";
import { HomePageFrame } from "./home-page-frame";

export function Homepage() {
  return (
    <HomePageFrame activePage="home">
      <HomepageHero />

      <section id="systems" className="brand-section brand-systems scroll-mt-24">
        <div className="brand-section-heading">
          <p className="brand-eyebrow">Systems</p>
          <div>
            <h2 className="brand-section-title">能力不是标签，是可以被验证的系统。</h2>
            <p className="brand-section-description">
              我把知识、行动与交付拆成清晰的工程边界，让 AI 从模型能力变成可靠的产品能力。
            </p>
          </div>
        </div>
        <HomepageOverview />
      </section>

      <HomepageProjects />
      <HomepageRoadmap />
      <HomepageContact />
    </HomePageFrame>
  );
}
