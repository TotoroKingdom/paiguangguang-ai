import { homepageNavigation } from "./homepage-data";

type SiteNavigationProps = { activePage?: string };

export function SiteNavigation({ activePage }: SiteNavigationProps) {
  const navigation = activePage === "home" ? homepageNavigation : [
    { label: "关于", href: "/#hero" },
    { label: "作品", href: "/#projects" },
    { label: "研究", href: "/#exploring" },
    { label: "成长", href: "/#journey" },
  ];

  return (
    <header className="brand-header">
      <div className="brand-header__inner">
        <a href="/#hero" className="brand-header__logo" aria-label="PaiGuangGuang 首页">PaiGuangGuang<span className="brand-header__logo-dot">.</span></a>
        <nav className="brand-header__nav" aria-label="主导航">
          {navigation.map((item) => (
            <a key={item.href} href={item.href}>{item.label}</a>
          ))}
        </nav>
        <a className="brand-header__external" href="/#contact">联系我</a>
      </div>
    </header>
  );
}
