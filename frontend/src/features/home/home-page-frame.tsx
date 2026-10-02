import type { ReactNode } from "react";

import { SiteNavigation } from "./homepage-navigation";

type HomePageFrameProps = {
  activePage: string;
  children: ReactNode;
  footerLabel?: string;
  footerCopy?: string;
  mainClassName?: string;
};

export function HomePageFrame({
  activePage,
  children,
  footerLabel = "TotoroKingdom / AI Agent Engineer",
  footerCopy = "Built with clarity, shipped with intent.",
  mainClassName = "home-main"
}: HomePageFrameProps) {
  return (
    <div className={`home-page${activePage === "home" ? " home-page--spatial" : ""}`}>
      <div className="relative z-10 brand-page-layer">
        <SiteNavigation activePage={activePage} />

        {activePage === "home" && <a className="home-skip-link" href="#home-content">跳到主要内容</a>}
        <main id={activePage === "home" ? "home-content" : undefined} className={mainClassName}>{children}</main>

        <footer className="brand-footer">
          <span className="brand-footer__label">{footerLabel}</span>
          <span>{footerCopy}</span>
        </footer>
      </div>
    </div>
  );
}
