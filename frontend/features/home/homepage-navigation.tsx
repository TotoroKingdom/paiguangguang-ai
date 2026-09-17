type SiteNavigationProps = {
  activePage?: string;
};

export function SiteNavigation(_props: SiteNavigationProps) {
  return (
    <header className="brand-header">
      <div className="brand-header__inner">
        <a href="/#hero" className="brand-header__logo" aria-label="回到首页">
          <span className="brand-header__mark">T</span>
          <span>TotoroKingdom</span>
        </a>

        <nav className="brand-header__nav" aria-label="主导航">
          <a href="/#projects">Work</a>
          <a href="/#systems">Systems</a>
          <a href="/#approach">Approach</a>
          <a href="/#contact">Contact</a>
        </nav>

        <div className="brand-header__availability">
          <span className="brand-header__availability-dot" />
          Open to work
        </div>
      </div>
    </header>
  );
}
