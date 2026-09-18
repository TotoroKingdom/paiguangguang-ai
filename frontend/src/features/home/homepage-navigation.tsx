type SiteNavigationProps = {
  activePage?: string;
};

export function SiteNavigation(_props: SiteNavigationProps) {
  return (
    <header className="brand-header">
      <div className="brand-header__inner">
        <a href="/#hero" className="brand-header__logo" aria-label="回到首页">
          <span className="brand-header__mark">TK</span>
          <span>TotoroKingdom<small>AI Systems</small></span>
        </a>

        <nav className="brand-header__nav" aria-label="主导航">
          <a href="/#projects">项目</a>
          <a href="/#systems">能力</a>
          <a href="/#approach">方法</a>
          <a href="/#contact">联系</a>
        </nav>

        <div className="brand-header__availability">
          <span className="brand-header__availability-dot" />
          Available for work
        </div>
      </div>
    </header>
  );
}
