const pagination = [
  { key: "home", index: "01", label: "首页", href: "/" },
  { key: "system", index: "02", label: "RAG 系统", href: "/rag" }
];

type SiteNavigationProps = {
  activePage?: string;
};

export function SiteNavigation({ activePage = "home" }: SiteNavigationProps) {
  const activeIndex = pagination.find((item) => item.key === activePage)?.index ?? pagination[0].index;

  return (
    <header className="site-header">
      <div className="site-header__inner">
        <a href="/#hero" className="brand" aria-label="回到首页">
          <span className="brand-mark">TG</span>
          <span className="brand-copy">
            <span className="brand-wordmark">TOTOROKINGDOM</span>
            <span className="brand-caption">/ AI systems</span>
          </span>
        </a>

        <div className="site-pagination" aria-label="页面分页栏">
          <span className="site-pagination__counter">
            <span>PAGE</span>
            <strong>{activeIndex}</strong>
            <span>/ {pagination.length.toString().padStart(2, "0")}</span>
          </span>

          <div className="site-pagination__items">
            {pagination.map((item) => (
              <a
                key={item.href}
                href={item.href}
                className="site-pagination__item"
                aria-current={item.key === activePage ? "page" : undefined}
              >
                <span className="site-pagination__number">{item.index}</span>
                <span className="site-pagination__label">{item.label}</span>
              </a>
            ))}
          </div>

          <span className="site-pagination__progress" aria-hidden="true">
            <span style={{ width: `${(Number(activeIndex) / pagination.length) * 100}%` }} />
          </span>
        </div>

        <div className="status-inline">
          <span className="status-dot" />
          Open to meaningful work
        </div>
      </div>
    </header>
  );
}
