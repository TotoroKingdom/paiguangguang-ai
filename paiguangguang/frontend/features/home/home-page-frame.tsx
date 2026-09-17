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
    <div className="home-page">
      <div className="pointer-events-none fixed inset-0 z-0 brand-page-grid" />

      <div className="relative z-10 brand-page-layer">
        <SiteNavigation activePage={activePage} />

        <main className={mainClassName}>{children}</main>

        <footer className="brand-footer">
          <span className="brand-footer__label">{footerLabel}</span>
          <span>{footerCopy}</span>
        </footer>
      </div>
    </div>
  );
}
