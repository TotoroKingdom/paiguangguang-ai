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
      <HomepageProjects />
      <section id="systems" className="brand-section brand-systems">
        <div className="brand-section-heading"><p className="brand-eyebrow">ENGINEERING FOCUS / 03</p><div><h2 className="brand-section-title">What I work on.</h2><p className="brand-section-description">围绕完整产品，而非孤立的技术关键词。</p></div></div>
        <HomepageOverview />
      </section>
      <HomepageRoadmap />
      <section id="about" className="brand-section brand-about">
        <p className="brand-eyebrow">ABOUT / 05</p>
        <div><h2>Engineer by practice.<br /><em>Builder by instinct.</em></h2><p>我是 TotoroKingdom，专注 AI 应用、Agent 系统与全栈工程。喜欢把复杂能力整理成清晰、可使用的产品，也持续记录从原型走向交付的工程过程。</p></div>
      </section>
      <HomepageContact />
    </HomePageFrame>
  );
}
