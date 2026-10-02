import { githubProfileHref, homepageNavigation } from "./homepage-data";

type SiteNavigationProps = { activePage?: string };

export function SiteNavigation({ activePage }: SiteNavigationProps) {
  return (
    <header className="brand-header">
      <div className="brand-header__inner">
        <a href="/#hero" className="brand-header__logo" aria-label="TotoroKingdom 首页">TotoroKingdom<span className="brand-header__logo-dot">.</span></a>
        <nav className="brand-header__nav" aria-label="主导航">
          {homepageNavigation.map((item) => (
            <a key={item.href} href={item.href} className={activePage === "home" && item.href === "/#projects" ? "brand-header__work" : undefined}>{item.label}</a>
          ))}
        </nav>
        <a className="brand-header__external" href={githubProfileHref} target="_blank" rel="noopener noreferrer">GitHub <span aria-hidden="true">↗</span><span className="sr-only">（新标签页打开）</span></a>
      </div>
    </header>
  );
}
