"use client";

import dynamic from "next/dynamic";
import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";

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

function GitHubIcon() {
    return (
        <svg aria-hidden="true" viewBox="0 0 24 24" className="h-7 w-7 fill-current">
            <path d="M12 2C6.48 2 2 6.58 2 12.26c0 4.54 2.87 8.39 6.84 9.75.5.1.68-.22.68-.49 0-.24-.01-.87-.01-1.71-2.78.62-3.37-1.37-3.37-1.37-.46-1.2-1.13-1.52-1.13-1.52-.92-.65.07-.64.07-.64 1.02.07 1.55 1.07 1.55 1.07.9 1.58 2.36 1.12 2.94.86.09-.67.35-1.12.63-1.38-2.22-.26-4.56-1.14-4.56-5.06 0-1.12.39-2.03 1.03-2.75-.1-.26-.45-1.31.1-2.72 0 0 .84-.28 2.75 1.05.8-.23 1.66-.35 2.52-.35.86 0 1.72.12 2.52.35 1.91-1.33 2.75-1.05 2.75-1.05.55 1.41.2 2.46.1 2.72.64.72 1.03 1.63 1.03 2.75 0 3.93-2.35 4.8-4.58 5.05.36.32.69.96.69 1.94 0 1.4-.01 2.53-.01 2.87 0 .27.18.6.69.49A10.28 10.28 0 0 0 22 12.26C22 6.58 17.52 2 12 2Z" />
        </svg>
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

                    <div className="relative flex min-h-[420px] flex-col items-center justify-center px-6 py-10 text-center sm:px-10">
                        <p className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-300/80">GET IN TOUCH</p>
                        <h3 className="mt-4 text-5xl font-light leading-none tracking-tight text-white sm:text-6xl">Contact.</h3>
                        <div className="mt-5 h-1 w-36 rounded-full bg-gradient-to-r from-fuchsia-400 via-violet-400 to-cyan-300" />

                        <a
                            className="mt-10 text-2xl font-medium tracking-tight text-white transition hover:text-cyan-200 sm:text-3xl"
                            href="mailto:totorokingdom@foxmail.com"
                        >
                            totorokingdom@foxmail.com
                        </a>

                        <a
                            aria-label="GitHub profile"
                            className="mt-8 inline-flex h-14 w-14 items-center justify-center rounded-full border border-white/15 bg-white/5 text-white transition hover:-translate-y-0.5 hover:border-cyan-300/60 hover:bg-cyan-300/10 hover:text-cyan-100 focus-visible:ring-2 focus-visible:ring-cyan-300/70"
                            href="https://github.com/TotoroKingdom"
                            rel="noreferrer"
                            target="_blank"
                        >
                            <GitHubIcon />
                        </a>
                    </div>
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
                </motion.div>
            </div>
        </section>
    );
}
