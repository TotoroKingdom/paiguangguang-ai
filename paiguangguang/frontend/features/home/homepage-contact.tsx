"use client";

import dynamic from "next/dynamic";
import { motion } from "framer-motion";

const SunCanvas = dynamic(() => import("./sun-canvas").then((module) => module.SunCanvas), {
  ssr: false,
  loading: () => (
    <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(56,189,248,0.2),transparent_35%),linear-gradient(180deg,rgba(15,23,42,0.96),rgba(2,6,23,0.98))]" />
  )
});

export function HomepageContact() {
  return (
    <section id="contact" className="space-y-6 px-4 sm:px-6 lg:px-8">
      <div className="max-w-3xl">
        <p className="text-sm font-semibold uppercase tracking-[0.32em] text-cyan-200/80">Contact</p>
        <h2 className="mt-3 text-3xl font-black text-white sm:text-4xl">Get in touch</h2>
      </div>

      <div className="grid gap-5 lg:grid-cols-[0.95fr_1.05fr]">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.2 }}
          transition={{ duration: 0.45 }}
          className="rounded-[28px] border border-white/10 bg-[radial-gradient(circle_at_top,rgba(139,92,246,0.14),transparent_24%),radial-gradient(circle_at_bottom_right,rgba(56,189,248,0.12),transparent_30%),linear-gradient(180deg,rgba(15,23,42,0.96),rgba(7,10,27,0.98))] p-5 shadow-[0_24px_80px_rgba(2,6,23,0.38)]"
        >
          <p className="text-sm font-medium uppercase tracking-[0.22em] text-slate-300/80">GET IN TOUCH</p>
          <h3 className="mt-4 text-5xl font-light tracking-tight text-white sm:text-6xl">Contact.</h3>
          <div className="mt-6 h-1 w-44 rounded-full bg-gradient-to-r from-fuchsia-400 via-violet-400 to-cyan-300" />

          <div className="mt-8 space-y-6">
            <label className="block space-y-3">
              <span className="text-lg font-medium text-white/90">Your Name</span>
              <div className="rounded-2xl border border-white/10 bg-[#17172d] px-6 py-5 text-lg text-white/35 shadow-inner shadow-black/20">
                What&apos;s your name?
              </div>
            </label>

            <label className="block space-y-3">
              <span className="text-lg font-medium text-white/90">Your Email</span>
              <div className="rounded-2xl border border-white/10 bg-[#17172d] px-6 py-5 text-lg text-white/35 shadow-inner shadow-black/20">
                What&apos;s your email?
              </div>
            </label>

            <label className="block space-y-3">
              <span className="text-lg font-medium text-white/90">Your Message</span>
              <div className="min-h-[250px] rounded-2xl border border-white/10 bg-[#17172d] px-6 py-5 text-lg text-white/35 shadow-inner shadow-black/20">
                What do you want to say?
              </div>
            </label>

            <div className="pt-2">
              <button
                type="button"
                className="rounded-2xl border border-violet-400/55 bg-transparent px-10 py-5 text-lg font-medium text-white transition hover:border-violet-300 hover:bg-violet-400/10"
              >
                Send Message
              </button>
            </div>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, scale: 0.97, y: 18 }}
          whileInView={{ opacity: 1, scale: 1, y: 0 }}
          viewport={{ once: true, amount: 0.2 }}
          transition={{ duration: 0.55 }}
          className="relative min-h-[360px] overflow-hidden rounded-[28px] border border-white/10 bg-[radial-gradient(circle_at_top,rgba(253,224,71,0.14),transparent_25%),radial-gradient(circle_at_bottom_right,rgba(56,189,248,0.18),transparent_30%),linear-gradient(180deg,rgba(15,23,42,0.96),rgba(2,6,23,0.98))]"
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
