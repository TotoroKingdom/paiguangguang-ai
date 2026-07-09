"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { motion } from "framer-motion";

const contactLinks = [
  { label: "入口", value: "Knowledge Agent", href: "/agents/knowledge" },
  { label: "浏览", value: "Browser Agent", href: "/agents/browser" },
  { label: "办公", value: "Office Agent", href: "/agents/office" },
  { label: "Contact", value: "Contact", href: "#contact" }
];

const SunCanvas = dynamic(() => import("./sun-canvas").then((module) => module.SunCanvas), {
  ssr: false,
  loading: () => (
    <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(56,189,248,0.2),transparent_35%),linear-gradient(180deg,rgba(15,23,42,0.96),rgba(2,6,23,0.98))]" />
  )
});

export function HomepageContact() {
  return (
    <section id="contact" className="space-y-6">
      <div className="max-w-3xl">
        <p className="text-sm font-semibold uppercase tracking-[0.32em] text-cyan-200/80">Contact</p>
        <h2 className="mt-3 text-3xl font-black text-white sm:text-4xl">左侧说明，右侧太阳，保留静态入口和视觉焦点</h2>
      </div>
      <div className="grid gap-5 lg:grid-cols-[0.85fr_1.15fr]">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.2 }}
          transition={{ duration: 0.45 }}
          className="order-1 rounded-[28px] border border-white/10 bg-white/5 p-5"
        >
          <p className="text-sm font-semibold uppercase tracking-[0.28em] text-cyan-200/70">Static links only</p>
          <p className="mt-4 text-sm leading-7 text-slate-300">
            这里保留静态联系说明和模块入口，不接入 EmailJS，也不暴露任何第三方 service key。
          </p>
          <div className="mt-5 space-y-3">
            {contactLinks.map((link) => (
              <Link
                key={`${link.label}-${link.value}`}
                href={link.href}
                className="flex items-center justify-between gap-4 rounded-2xl border border-white/10 bg-slate-950/60 px-4 py-3 transition hover:border-cyan-300/25 hover:bg-white/10"
              >
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">{link.label}</p>
                  <p className="mt-1 text-base font-semibold text-white">{link.value}</p>
                </div>
                <span className="text-sm text-cyan-100">→</span>
              </Link>
            ))}
          </div>
        </motion.div>
        <motion.div
          initial={{ opacity: 0, scale: 0.97, y: 18 }}
          whileInView={{ opacity: 1, scale: 1, y: 0 }}
          viewport={{ once: true, amount: 0.2 }}
          transition={{ duration: 0.55 }}
          className="order-2 relative min-h-[360px] overflow-hidden rounded-[28px] border border-white/10 bg-[radial-gradient(circle_at_top,rgba(253,224,71,0.14),transparent_25%),radial-gradient(circle_at_bottom_right,rgba(56,189,248,0.18),transparent_30%),linear-gradient(180deg,rgba(15,23,42,0.96),rgba(2,6,23,0.98))]"
        >
          <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.04)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.04)_1px,transparent_1px)] bg-[size:26px_26px] opacity-15" />
          <SunCanvas />
          <div className="pointer-events-none absolute inset-0 flex items-end justify-between p-5">
            <div className="max-w-sm rounded-2xl border border-white/10 bg-slate-950/55 p-4 backdrop-blur-sm">
              <p className="text-xs font-semibold uppercase tracking-[0.3em] text-amber-200/80">Client-only canvas</p>
              <p className="mt-2 text-sm leading-6 text-slate-300">
                WebGL 视觉通过 client component 呈现，避免 SSR 和 hydration error。
              </p>
            </div>
            <div className="hidden rounded-full border border-white/10 bg-white/5 px-3 py-2 text-xs font-medium text-slate-200 md:block">
              Fixed height on mobile
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
