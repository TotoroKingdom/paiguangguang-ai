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
  footerLabel = "TG / AI SYSTEMS",
  footerCopy = "Built with clarity, shipped with intent.",
  mainClassName = "home-main"
}: HomePageFrameProps) {
  return (
    <div className="home-page">
      <div className="pointer-events-none fixed inset-0 z-0 page-grid opacity-55" />

      <div className="relative z-10">
        <SiteNavigation activePage={activePage} />

        <main className={mainClassName}>{children}</main>

        <footer className="home-footer">
          <span className="font-mono">{footerLabel}</span>
          <span>{footerCopy}</span>
        </footer>
      </div>
    </div>
  );
}
