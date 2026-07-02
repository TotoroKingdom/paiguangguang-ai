import Link from "next/link";

const navItems = [
  { href: "/", label: "Home" },
  { href: "/agents/knowledge", label: "Knowledge" },
  { href: "/agents/browser", label: "Browser" },
  { href: "/agents/office", label: "Office" },
  { href: "/architecture", label: "Architecture" }
];

export function SiteNav() {
  return (
    <header className="border-b border-ink/10 bg-paper/85 backdrop-blur">
      <nav className="mx-auto flex max-w-6xl flex-col gap-4 px-5 py-4 md:flex-row md:items-center md:justify-between">
        <Link href="/" className="text-lg font-semibold tracking-normal text-ink">
          Pai Guangguang AI Lab
        </Link>
        <div className="flex flex-wrap gap-2">
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="border border-ink/10 bg-white/55 px-3 py-2 text-sm font-medium text-ink transition hover:border-tide/40 hover:bg-white"
            >
              {item.label}
            </Link>
          ))}
        </div>
      </nav>
    </header>
  );
}
