"use client";

import dynamic from "next/dynamic";
import {useEffect, useRef, useState} from "react";
import {motion} from "framer-motion";

const SunCanvas = dynamic(() => import("./sun-canvas").then((module) => module.SunCanvas), {
    ssr: false,
    loading: () => (
        <div
            className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(56,189,248,0.2),transparent_35%),linear-gradient(180deg,rgba(15,23,42,0.96),rgba(2,6,23,0.98))]"/>
    )
});

function SunCanvasFallback() {
    return (
        <div
            aria-hidden="true"
            className="absolute inset-0 bg-[radial-gradient(circle_at_58%_42%,rgba(250,204,21,0.52),transparent_11%),radial-gradient(circle_at_58%_42%,rgba(251,146,60,0.24),transparent_23%),radial-gradient(circle_at_45%_55%,rgba(56,189,248,0.18),transparent_34%),linear-gradient(180deg,rgba(15,23,42,0.96),rgba(2,6,23,0.98))]"
        />
    );
}

function LazySunCanvas() {
    const hostRef = useRef<HTMLDivElement>(null);
    const [shouldMountCanvas, setShouldMountCanvas] = useState(false);
    const [isCanvasActive, setIsCanvasActive] = useState(false);

    useEffect(() => {
        const host = hostRef.current;
        if (!host) {
            return;
        }

        const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
        const isSmallViewport = window.matchMedia("(max-width: 767px)").matches;

        if (prefersReducedMotion || isSmallViewport || !("IntersectionObserver" in window)) {
            return;
        }

        const observer = new IntersectionObserver(
            ([entry]) => {
                if (entry.isIntersecting) {
                    setShouldMountCanvas(true);
                }
                setIsCanvasActive(entry.isIntersecting);
            },
            {rootMargin: "280px 0px"}
        );

        observer.observe(host);

        return () => observer.disconnect();
    }, []);

    return (
        <div ref={hostRef} className="absolute inset-0">
            <SunCanvasFallback/>
            {shouldMountCanvas ? <SunCanvas active={isCanvasActive}/> : null}
        </div>
    );
}

export function HomepageContact() {
    return (
        <section id="contact" className="mx-auto w-full max-w-[1500px] space-y-6 px-4 pb-6 sm:px-6 lg:px-8">
            <div className="max-w-3xl">
                <p className="text-sm font-semibold uppercase tracking-[0.32em] text-cyan-200/80">Contact</p>
                <h2 className="mt-3 text-3xl font-black text-white sm:text-4xl">Get in touch</h2>
            </div>

            <div className="grid gap-5 lg:grid-cols-[0.92fr_1.08fr]">
                <motion.div
                    initial={{opacity: 0, y: 16}}
                    whileInView={{opacity: 1, y: 0}}
                    viewport={{once: true, amount: 0.2}}
                    transition={{duration: 0.45}}
                    className="relative overflow-hidden rounded-[30px] border border-white/10 bg-[radial-gradient(circle_at_22%_0%,rgba(139,92,246,0.28),transparent_28%),radial-gradient(circle_at_90%_18%,rgba(56,189,248,0.14),transparent_26%),linear-gradient(180deg,rgba(17,19,42,0.98),rgba(8,10,28,0.99))] p-5 shadow-[0_24px_80px_rgba(2,6,23,0.42)] sm:p-7"
                >
                    <div
                        className="pointer-events-none absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.055)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.055)_1px,transparent_1px)] bg-[size:22px_22px] opacity-[0.11]"/>
                    <div
                        className="pointer-events-none absolute -right-16 top-10 h-48 w-48 rounded-full bg-cyan-300/10 blur-3xl"/>

                    <div className="relative">
                        <p className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-300/80">GET IN
                            TOUCH</p>
                        <h3 className="mt-4 text-5xl font-light leading-none tracking-tight text-white sm:text-6xl">Contact.</h3>
                        <div
                            className="mt-5 h-1 w-36 rounded-full bg-gradient-to-r from-fuchsia-400 via-violet-400 to-cyan-300"/>
                    </div>

                    <form className="relative mt-7 space-y-5">
                        <label className="block space-y-2.5">
                            <span className="text-base font-medium text-white/90">Your Name</span>
                            <input
                                name="name"
                                placeholder="What's your name?"
                                className="w-full rounded-2xl border border-white/10 bg-[#17172d] px-6 py-5 text-lg text-white placeholder:text-white/35 shadow-inner shadow-black/20"
                            />
                        </label>

                        <label className="block space-y-2.5">
                            <span className="text-base font-medium text-white/90">Your Email</span>
                            <input
                                aria-label="Your email"
                                className="h-14 w-full rounded-[18px] border border-white/10 bg-[#16172d]/95 px-5 text-base text-white outline-none shadow-inner shadow-black/20 transition placeholder:text-slate-500 focus:border-violet-300/65 focus:bg-[#191a34]"
                                placeholder="What's your email?"
                                type="email"
                            />
                        </label>

                        <label className="block space-y-2.5">
                            <span className="text-base font-medium text-white/90">Your Message</span>
                            <textarea
                                name="message"
                                placeholder="What do you want to say?"
                                className="min-h-[250px] w-full rounded-2xl border border-white/10 bg-[#17172d] px-6 py-5 text-lg text-white placeholder:text-white/35 shadow-inner shadow-black/20"
                            />
                        </label>

                        <div className="pt-1">
                            <button
                                aria-label="Send message"
                                type="button"
                                className="rounded-[18px] border border-violet-300/50 bg-gradient-to-r from-violet-500 to-fuchsia-500 px-8 py-4 text-base font-semibold text-white shadow-[0_18px_45px_rgba(124,58,237,0.32)] transition hover:-translate-y-0.5 hover:shadow-[0_22px_55px_rgba(124,58,237,0.42)]"
                            >
                                Send Message
                            </button>
                        </div>
                    </form>
                </motion.div>

                <motion.div
                    initial={{opacity: 0, scale: 0.97, y: 18}}
                    whileInView={{opacity: 1, scale: 1, y: 0}}
                    viewport={{once: true, amount: 0.2}}
                    transition={{duration: 0.55}}
                    className="relative min-h-[320px] overflow-hidden rounded-[30px] border border-white/10 bg-[radial-gradient(circle_at_top,rgba(253,224,71,0.14),transparent_25%),radial-gradient(circle_at_bottom_right,rgba(56,189,248,0.18),transparent_30%),linear-gradient(180deg,rgba(15,23,42,0.96),rgba(2,6,23,0.98))] sm:min-h-[420px] lg:min-h-full"
                >
                    <div
                        className="pointer-events-none absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.04)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.04)_1px,transparent_1px)] bg-[size:26px_26px] opacity-[0.14]"/>
                    <LazySunCanvas/>
                    <div
                        className="pointer-events-none absolute inset-0 flex items-end justify-between gap-4 p-5 sm:p-6">
                        <div
                            className="max-w-xs rounded-2xl border border-white/10 bg-slate-950/45 p-4 backdrop-blur-md">
                            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-amber-200/80">Open to
                                build</p>
                            <p className="mt-2 text-sm leading-6 text-slate-300">AI applications, RAG systems and agent
                                workflows.</p>
                        </div>
                        <div
                            className="hidden rounded-full border border-white/10 bg-white/5 px-3.5 py-2 text-xs font-medium text-slate-200 backdrop-blur-sm md:block">
                            2026 Portfolio
                        </div>
                    </div>
                </motion.div>
            </div>
        </section>
    );
}
