"use client";

import { motion } from "framer-motion";

import type { TechStackItem } from "./homepage-data";
import { techStack } from "./homepage-data";

const categoryLabels: Record<TechStackItem["category"], string> = {
  frontend: "Frontend",
  backend: "Backend",
  ai: "AI",
  storage: "Storage",
  workflow: "Workflow",
  delivery: "Delivery",
  response: "Response"
};

const categoryStyles: Record<TechStackItem["category"], string> = {
  frontend: "from-sky-400/20 via-cyan-300/10 to-white/5 text-sky-100 border-sky-300/20",
  backend: "from-emerald-400/20 via-teal-300/10 to-white/5 text-emerald-100 border-emerald-300/20",
  ai: "from-fuchsia-400/20 via-pink-300/10 to-white/5 text-fuchsia-100 border-fuchsia-300/20",
  storage: "from-amber-400/20 via-orange-300/10 to-white/5 text-amber-100 border-amber-300/20",
  workflow: "from-violet-400/20 via-purple-300/10 to-white/5 text-violet-100 border-violet-300/20",
  delivery: "from-slate-200/15 via-slate-300/10 to-white/5 text-slate-100 border-white/10",
  response: "from-cyan-400/20 via-blue-300/10 to-white/5 text-cyan-100 border-cyan-300/20"
};

const iconStyles: Record<TechStackItem["category"], string> = {
  frontend: "border-sky-200/20 bg-sky-300/10 text-sky-100 shadow-sky-300/10",
  backend: "border-emerald-200/20 bg-emerald-300/10 text-emerald-100 shadow-emerald-300/10",
  ai: "border-fuchsia-200/20 bg-fuchsia-300/10 text-fuchsia-100 shadow-fuchsia-300/10",
  storage: "border-amber-200/20 bg-amber-300/10 text-amber-100 shadow-amber-300/10",
  workflow: "border-violet-200/20 bg-violet-300/10 text-violet-100 shadow-violet-300/10",
  delivery: "border-slate-100/20 bg-slate-100/10 text-slate-100 shadow-slate-100/10",
  response: "border-cyan-200/20 bg-cyan-300/10 text-cyan-100 shadow-cyan-300/10"
};

function TechIcon({ item }: { item: TechStackItem }) {
  const common = "h-6 w-6";

  const glyph = (() => {
    switch (item.name) {
      case "Next.js":
        return (
          <svg viewBox="0 0 24 24" className={common} aria-hidden="true">
            <path d="M6 18V6l9.5 12M18 6v12" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
            <path d="M6 6l12 12" fill="none" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" opacity="0.45" />
          </svg>
        );
      case "Java":
        return (
          <svg viewBox="0 0 24 24" className={common} aria-hidden="true">
            <path d="M8 13h7.5a3.5 3.5 0 0 1 0 7H9a4 4 0 0 1-4-4v-3h3Z" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
            <path d="M9 4c2 1.8-1.5 3.1.8 5M13 3c2.2 2-1.7 3.5.8 6" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
          </svg>
        );
      case "FastAPI":
        return (
          <svg viewBox="0 0 24 24" className={common} aria-hidden="true">
            <path d="M13 2 5 13h6l-1 9 9-13h-6l0-7Z" fill="currentColor" opacity="0.9" />
          </svg>
        );
      case "DeepSeek":
        return (
          <svg viewBox="0 0 24 24" className={common} aria-hidden="true">
            <path d="M12 3 20 8v8l-8 5-8-5V8l8-5Z" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
            <path d="M8 10h4.5a3 3 0 0 1 0 6H8v-6Z" fill="currentColor" opacity="0.78" />
          </svg>
        );
      case "LangGraph":
        return (
          <svg viewBox="0 0 24 24" className={common} aria-hidden="true">
            <circle cx="6" cy="7" r="2.2" fill="currentColor" />
            <circle cx="18" cy="7" r="2.2" fill="currentColor" opacity="0.75" />
            <circle cx="12" cy="17" r="2.4" fill="currentColor" opacity="0.9" />
            <path d="M8 7h8M7.4 8.8 10.8 15M16.6 8.8 13.2 15" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" opacity="0.55" />
          </svg>
        );
      case "LangChain":
        return (
          <svg viewBox="0 0 24 24" className={common} aria-hidden="true">
            <path d="M8.6 13.5 7 15.1a4 4 0 1 1-5.7-5.7L4 6.7a4 4 0 0 1 5.7 0" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
            <path d="m15.4 10.5 1.6-1.6a4 4 0 1 1 5.7 5.7L20 17.3a4 4 0 0 1-5.7 0" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
            <path d="M8.5 12h7" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" opacity="0.65" />
          </svg>
        );
      case "Milvus":
        return (
          <svg viewBox="0 0 24 24" className={common} aria-hidden="true">
            <circle cx="6" cy="7" r="2.3" fill="currentColor" />
            <circle cx="18" cy="7" r="2.3" fill="currentColor" opacity="0.75" />
            <circle cx="12" cy="17" r="2.8" fill="currentColor" opacity="0.9" />
            <path d="M8 8.5 11 15M16 8.5 13 15M8.3 7h7.4" stroke="currentColor" strokeWidth="1.5" opacity="0.45" />
          </svg>
        );
      case "Redis":
        return (
          <svg viewBox="0 0 24 24" className={common} aria-hidden="true">
            <path d="M4 7.5 12 4l8 3.5-8 3.5-8-3.5Z" fill="currentColor" opacity="0.85" />
            <path d="m4 12 8 3.5 8-3.5M4 16l8 3.5 8-3.5" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        );
      case "MySQL":
        return (
          <svg viewBox="0 0 24 24" className={common} aria-hidden="true">
            <ellipse cx="12" cy="6" rx="7" ry="3" fill="none" stroke="currentColor" strokeWidth="1.7" />
            <path d="M5 6v9c0 1.7 3.1 3 7 3s7-1.3 7-3V6M5 10c0 1.7 3.1 3 7 3s7-1.3 7-3" fill="none" stroke="currentColor" strokeWidth="1.7" />
          </svg>
        );
      case "RAG":
        return (
          <svg viewBox="0 0 24 24" className={common} aria-hidden="true">
            <path d="M6 4h8l4 4v12H6V4Z" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round" />
            <path d="M14 4v5h4M8.5 13h7M8.5 16h5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
            <circle cx="6" cy="4" r="1.5" fill="currentColor" />
          </svg>
        );
      case "Agent":
        return (
          <svg viewBox="0 0 24 24" className={common} aria-hidden="true">
            <circle cx="12" cy="12" r="3" fill="currentColor" />
            <circle cx="6" cy="6" r="2" fill="currentColor" opacity="0.75" />
            <circle cx="18" cy="7" r="2" fill="currentColor" opacity="0.75" />
            <circle cx="17" cy="18" r="2" fill="currentColor" opacity="0.75" />
            <path d="M7.5 7.5 10 10M15 9l1.5-1M14.2 14.2l1.4 1.7" stroke="currentColor" strokeWidth="1.5" opacity="0.55" />
          </svg>
        );
      case "VibeCoding":
        return (
          <svg viewBox="0 0 24 24" className={common} aria-hidden="true">
            <rect x="4" y="5" width="16" height="14" rx="3" fill="none" stroke="currentColor" strokeWidth="1.8" />
            <path d="m8 10 3 2-3 2M13.5 15h3" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        );
      case "Git":
        return (
          <svg viewBox="0 0 24 24" className={common} aria-hidden="true">
            <path d="M12 3 21 12l-9 9-9-9 9-9Z" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round" />
            <circle cx="9" cy="9" r="1.7" fill="currentColor" />
            <circle cx="15" cy="15" r="1.7" fill="currentColor" />
            <path d="M9 10.7V12a3 3 0 0 0 3 3h1.3M9 10.7 15 15" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
        );
      case "Docker":
        return <img src="/homepage/tech/docker.png" alt="" className="h-6 w-6 object-contain" />;
      case "Jenkins":
        return (
          <svg viewBox="0 0 24 24" className={common} aria-hidden="true">
            <circle cx="12" cy="9" r="4" fill="none" stroke="currentColor" strokeWidth="1.7" />
            <path d="M7 20v-2.2A4.8 4.8 0 0 1 11.8 13h.4A4.8 4.8 0 0 1 17 17.8V20M8.5 8h7M9 4.5 7.8 7.5M15 4.5l1.2 3" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
          </svg>
        );
      default:
        return <span className="text-sm font-black">{item.name.slice(0, 1)}</span>;
    }
  })();

  return (
    <div className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl border shadow-[0_0_30px] ${iconStyles[item.category]}`}>
      {glyph}
    </div>
  );
}

export function HomepageTechStack() {
  return (
    <section id="tech-stack" className="space-y-6">
      <div className="mx-auto max-w-3xl text-center">
        <p className="text-sm font-semibold uppercase tracking-[0.32em] text-cyan-200/80">Tech Stack</p>
        {/*<h2 className="mt-3 text-3xl font-black text-white sm:text-4xl">漂浮式技术墙，强调能力而不是装饰图标</h2>*/}
      </div>
      <div className="relative mx-auto max-w-6xl overflow-hidden rounded-[28px] border border-white/10 bg-[radial-gradient(circle_at_top,rgba(14,165,233,0.15),transparent_28%),radial-gradient(circle_at_bottom_right,rgba(217,70,239,0.13),transparent_30%),linear-gradient(180deg,rgba(15,23,42,0.95),rgba(2,6,23,0.95))] p-4 sm:p-6">
        <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.04)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.04)_1px,transparent_1px)] bg-[size:28px_28px] opacity-20" />
        <div className="relative mx-auto grid max-w-[720px] justify-center justify-items-center gap-4 [grid-template-columns:repeat(2,150px)] sm:[grid-template-columns:repeat(3,150px)] xl:[grid-template-columns:repeat(4,150px)]">
          {techStack.map((item, index) => (
            <motion.div
              key={`${item.category}-${item.name}`}
              initial={{ opacity: 0, scale: 0.95, y: 18 }}
              whileInView={{ opacity: 1, scale: 1, y: 0 }}
              viewport={{ once: true, amount: 0.2 }}
              transition={{ duration: 0.45, delay: index * 0.035 }}
              whileHover={{ y: -6, rotate: index % 2 === 0 ? -1 : 1 }}
              className={`group relative flex aspect-square w-full max-w-[150px] overflow-hidden rounded-2xl border bg-white/[0.035] p-4 text-center backdrop-blur-sm transition duration-500 hover:border-cyan-200/35 ${categoryStyles[item.category]}`}
            >
              <div className={`pointer-events-none absolute inset-0 bg-gradient-to-br ${categoryStyles[item.category]} opacity-0 transition duration-500 group-hover:opacity-100`} />
              <div className="pointer-events-none absolute -right-8 -top-8 h-20 w-20 rounded-full bg-white/10 blur-2xl opacity-0 transition duration-500 group-hover:opacity-100" />
              <div className="relative z-10 flex h-full w-full flex-col items-center justify-center">
                <TechIcon item={item} />
                <p className="mt-4 text-[9px] font-semibold uppercase tracking-[0.2em] text-white/55">
                  {categoryLabels[item.category]}
                </p>
                <p className="mt-1 max-w-full truncate text-sm font-semibold text-white">{item.name}</p>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
