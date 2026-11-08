import Link from "next/link";
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
        <Link href="/#hero" className="brand-header__logo" aria-label="PaiGuangGuang 首页">PaiGuangGuang<span className="brand-header__logo-dot">.</span></Link>
        <nav className="brand-header__nav" aria-label="主导航">
          {navigation.map((item) => (
            <Link key={item.href} href={item.href}>{item.label}</Link>
          ))}
        </nav>
        <Link className="brand-header__external" href="/#contact">联系我</Link>
      </div>
    </header>
  );
}
