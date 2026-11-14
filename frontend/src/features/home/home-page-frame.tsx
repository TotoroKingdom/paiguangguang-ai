import type { ReactNode } from "react";

import { SiteNavigation } from "./homepage-navigation";

type HomePageFrameProps = {
  activePage: string;
  children: ReactNode;
  footerLabel?: string;
  footerCopy?: string;
  mainClassName?: string;
  overlay?: ReactNode;
  theme?: "default" | "spatial";
};

export function HomePageFrame({
  activePage,
  children,
  footerLabel = "TotoroKingdom / AI Agent Engineer",
  footerCopy = "让系统清晰，让交付可靠。",
  mainClassName = "home-main",
  overlay,
  theme
}: HomePageFrameProps) {
  const resolvedTheme = theme ?? (activePage === "home" ? "spatial" : "default");

  return (
    <div className={`home-page${resolvedTheme === "spatial" ? " home-page--spatial" : ""}`}>
      {overlay}
      <div className="relative z-10 brand-page-layer">
        <SiteNavigation />

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
