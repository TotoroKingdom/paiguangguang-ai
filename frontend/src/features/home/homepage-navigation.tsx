type SiteNavigationProps = { activePage?: string };

export function SiteNavigation(_props: SiteNavigationProps) {
  return (
    <header className="brand-header">
      <div className="brand-header__inner">
        <a href="/#hero" className="brand-header__logo" aria-label="TotoroKingdom 首页">TotoroKingdom<span className="brand-header__logo-dot">.</span></a>
        <nav className="brand-header__nav" aria-label="主导航">
          <a href="/#projects">Work</a>
          <a href="/#about">About</a>
          <a href="/rag">Notes</a>
        </nav>
        <a className="brand-header__external" href="https://github.com/TotoroKingdom" target="_blank" rel="noreferrer">GitHub <span aria-hidden="true">↗</span></a>
      </div>
    </header>
  );
}
