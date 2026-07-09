"use client";

import {type ReactNode} from "react";
import {motion} from "framer-motion";

import {overviewCards} from "./homepage-data";

const glyphStyles: Record<(typeof overviewCards)[number]["accent"], string> = {
    green: "from-emerald-300 via-cyan-300 to-lime-300",
    purple: "from-fuchsia-300 via-violet-300 to-cyan-300",
    blue: "from-sky-300 via-cyan-300 to-blue-300",
    pink: "from-rose-300 via-fuchsia-300 to-pink-300"
};

const glowStyles: Record<(typeof overviewCards)[number]["accent"], string> = {
    green: "shadow-emerald-300/25",
    purple: "shadow-fuchsia-300/25",
    blue: "shadow-cyan-300/25",
    pink: "shadow-pink-300/25"
};

const skillLabels = [
    "RAG Engineer",
    "Agent Workflow",
    "Full-stack AI",
    "VibeCoding"
];

function RagLogo() {
    return (
        <svg viewBox="0 0 96 96" className="h-20 w-20 text-cyan-50/90">
            <circle
                cx="48"
                cy="48"
                r="30"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
                opacity="0.22"
            />
            <circle
                cx="48"
                cy="48"
                r="20"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeDasharray="4 7"
                opacity="0.45"
            />
            <path
                d="M31 34h21l13 13v18H31V34Z"
                fill="rgba(255,255,255,0.05)"
                stroke="currentColor"
                strokeWidth="2.2"
                strokeLinejoin="round"
            />
            <path
                d="M52 34v14h13"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                opacity="0.8"
            />
            <path
                d="M38 53h20M38 61h13"
                stroke="currentColor"
                strokeWidth="2.2"
                strokeLinecap="round"
                opacity="0.8"
            />
            <circle cx="28" cy="30" r="3" fill="currentColor"/>
            <circle cx="69" cy="42" r="3" fill="currentColor"/>
            <circle cx="35" cy="72" r="3" fill="currentColor"/>
            <path
                d="M30 31 39 41M66 44 59 53M37 70l8-9"
                stroke="currentColor"
                strokeWidth="1.4"
                opacity="0.5"
            />
        </svg>
    );
}

function AgentLogo() {
    return (
        <svg viewBox="0 0 96 96" className="h-20 w-20 text-cyan-50/90">
            <path
                d="M48 15 76 31v34L48 81 20 65V31l28-16Z"
                fill="rgba(255,255,255,0.04)"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinejoin="round"
                opacity="0.75"
            />
            <path
                d="M48 28 65 38v20L48 68 31 58V38l17-10Z"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.7"
                strokeDasharray="5 6"
                strokeLinejoin="round"
                opacity="0.45"
            />
            <circle cx="48" cy="48" r="7" fill="currentColor" opacity="0.95"/>
            <circle cx="48" cy="25" r="4" fill="currentColor"/>
            <circle cx="69" cy="60" r="4" fill="currentColor"/>
            <circle cx="27" cy="60" r="4" fill="currentColor"/>
            <path
                d="M48 29v12M54 52l11 6M42 52l-11 6"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                opacity="0.65"
            />
            <path
                d="M36 19c6-5 18-5 24 0M28 74c10 9 30 9 40 0"
                stroke="currentColor"
                strokeWidth="1.6"
                strokeLinecap="round"
                opacity="0.35"
            />
        </svg>
    );
}

function FullStackLogo() {
    return (
        <svg viewBox="0 0 96 96" className="h-20 w-20 text-cyan-50/90">
            <path
                d="M48 18 73 31 48 44 23 31 48 18Z"
                fill="rgba(255,255,255,0.06)"
                stroke="currentColor"
                strokeWidth="2.2"
                strokeLinejoin="round"
            />
            <path
                d="M25 43 48 55l23-12M25 56l23 12 23-12"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.2"
                strokeLinecap="round"
                strokeLinejoin="round"
                opacity="0.75"
            />
            <path
                d="M48 44v24"
                stroke="currentColor"
                strokeWidth="1.7"
                strokeDasharray="4 6"
                strokeLinecap="round"
                opacity="0.5"
            />
            <circle cx="48" cy="18" r="3" fill="currentColor"/>
            <circle cx="23" cy="31" r="3" fill="currentColor"/>
            <circle cx="73" cy="31" r="3" fill="currentColor"/>
            <circle cx="48" cy="68" r="3" fill="currentColor"/>
            <path
                d="M18 24c5-8 13-13 23-15M78 24c-5-8-13-13-23-15M19 73c7 8 17 12 29 12s22-4 29-12"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                opacity="0.28"
            />
        </svg>
    );
}

function VibeLogo() {
    return (
        <svg viewBox="0 0 96 96" className="h-20 w-20 text-cyan-50/90">
            <rect
                x="23"
                y="28"
                width="50"
                height="36"
                rx="9"
                fill="rgba(255,255,255,0.05)"
                stroke="currentColor"
                strokeWidth="2.2"
            />
            <path
                d="m36 42 8 6-8 6M53 56h10"
                stroke="currentColor"
                strokeWidth="2.7"
                strokeLinecap="round"
                strokeLinejoin="round"
            />
            <path
                d="M48 15v9M48 72v9M20 48h-8M84 48h-8"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
                opacity="0.45"
            />
            <path
                d="M67 17 62 27M29 17l5 10M67 79l-5-10M29 79l5-10"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                opacity="0.35"
            />
            <circle cx="48" cy="48" r="31" fill="none" stroke="currentColor" strokeWidth="1.4" strokeDasharray="3 8"
                    opacity="0.28"/>
            <circle cx="72" cy="24" r="3" fill="currentColor"/>
            <circle cx="24" cy="72" r="3" fill="currentColor"/>
            <path
                d="M69 27 61 35M27 69l8-8"
                stroke="currentColor"
                strokeWidth="1.4"
                opacity="0.55"
            />
        </svg>
    );
}

const logos: ReactNode[] = [
    <RagLogo key="rag"/>,
    <AgentLogo key="agent"/>,
    <FullStackLogo key="full-stack"/>,
    <VibeLogo key="vibe"/>
];

export function HomepageOverview() {
    return (
        <section id="overview" className="mx-auto w-full max-w-[1500px] space-y-8 px-4 text-center">
            <div className="mx-auto max-w-3xl">
                <p className="text-sm font-semibold uppercase tracking-[0.32em] text-cyan-200/80">
                    Core Competencies
                </p>

                <h2 className="mt-3 text-3xl font-black text-white sm:text-4xl">
                    我的核心能力
                </h2>
            </div>

            <div className="mx-auto grid w-full max-w-6xl justify-center justify-items-center gap-8 sm:grid-cols-2 xl:grid-cols-4">
                {overviewCards.map((card, index) => (
                    <motion.article
                        key={card.title}
                        initial={{opacity: 0, y: 16}}
                        whileInView={{opacity: 1, y: 0}}
                        viewport={{once: true, amount: 0.3}}
                        transition={{duration: 0.45, delay: index * 0.05}}
                        className="group relative h-[380px] w-full max-w-[330px] overflow-hidden rounded-[38px] border border-cyan-200/10 bg-white/5 p-[1px] transition duration-500 hover:-translate-y-3 hover:border-cyan-200/40"
                    >
                        {/* hover 外层渐变光晕 */}
                        <div
                            className={`absolute -inset-12 bg-gradient-to-br ${glyphStyles[card.accent]} opacity-0 blur-3xl transition duration-700 group-hover:opacity-35`}
                        />

                        {/* 扫描光 */}
                        <div
                            className="absolute inset-0 translate-y-[-120%] bg-gradient-to-b from-transparent via-cyan-100/20 to-transparent opacity-0 transition duration-700 group-hover:translate-y-[120%] group-hover:opacity-100"/>

                        {/* 卡片主体 */}
                        <div
                            className="relative flex h-full flex-col overflow-hidden rounded-[37px] bg-[radial-gradient(circle_at_50%_18%,rgba(125,211,252,0.18),transparent_34%),radial-gradient(circle_at_50%_88%,rgba(217,70,239,0.16),transparent_40%),linear-gradient(180deg,rgba(15,23,42,0.96),rgba(2,6,23,0.99))] p-8 text-center backdrop-blur-sm transition duration-500 group-hover:bg-slate-950/70">
                            {/* 顶部淡光 */}
                            <div
                                className={`pointer-events-none absolute left-1/2 top-10 h-40 w-40 -translate-x-1/2 rounded-full bg-gradient-to-br ${glyphStyles[card.accent]} opacity-15 blur-3xl transition duration-700 group-hover:opacity-30`}
                            />

                            {/* Logo 区域：改回渐变块样式 */}
                            <div className="relative z-10 flex flex-1 items-center justify-center pb-16">
                                <div
                                    className={`relative flex h-32 w-32 items-center justify-center rounded-[36px] bg-gradient-to-br ${glyphStyles[card.accent]} shadow-[0_0_70px] ${glowStyles[card.accent]} transition duration-500 group-hover:scale-110 group-hover:rotate-3`}
                                >
                                    <div className="absolute inset-[2px] rounded-[34px] bg-white/20 blur-[1px]"/>

                                    <div
                                        className="absolute inset-[7px] rounded-[29px] border border-white/30 bg-slate-950/10"/>

                                    <div
                                        className="absolute -right-2 -top-2 h-5 w-5 rounded-full border border-white/40 bg-white/20 shadow-[0_0_18px_rgba(255,255,255,0.5)]"/>

                                    <div
                                        className="absolute -bottom-2 -left-2 h-4 w-4 rounded-full border border-cyan-100/50 bg-cyan-100/20 shadow-[0_0_18px_rgba(103,232,249,0.6)]"/>

                                    <div
                                        className="relative z-10 flex h-full w-full items-center justify-center drop-shadow-[0_0_16px_rgba(255,255,255,0.45)]">
                                        <div className="flex h-20 w-20 items-center justify-center">
                                            {logos[index] ?? <RagLogo/>}
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* 底部能力标签 */}
                            <div className="absolute bottom-9 left-8 right-8 z-20">
                                <div className="mx-auto mb-5 flex w-full max-w-[220px] items-center justify-center">
                                    <div
                                        className="h-px flex-1 bg-gradient-to-r from-transparent via-cyan-100/60 to-cyan-100/10"/>
                                    <div
                                        className="mx-3 h-1.5 w-1.5 rounded-full bg-cyan-100 shadow-[0_0_18px_rgba(207,250,254,0.95)] transition duration-500 group-hover:bg-fuchsia-100 group-hover:shadow-[0_0_18px_rgba(217,70,239,0.95)]"/>
                                    <div
                                        className="h-px flex-1 bg-gradient-to-r from-cyan-100/10 via-fuchsia-100/60 to-transparent"/>
                                </div>

                                <div
                                    className="mx-auto w-fit rounded-full border border-cyan-100/15 bg-white/[0.045] px-5 py-2.5 text-[11px] font-semibold uppercase tracking-[0.24em] text-cyan-50/75 shadow-[0_0_28px_rgba(56,189,248,0.08)] backdrop-blur-md transition duration-500 group-hover:border-cyan-100/35 group-hover:bg-cyan-100/10 group-hover:text-cyan-50">
                                    {skillLabels[index] ?? "RAG Engineer"}
                                </div>
                            </div>

                            {/* 底部装饰码 */}
                            <div
                                className="pointer-events-none absolute bottom-4 left-1/2 flex -translate-x-1/2 gap-1.5 opacity-20 transition duration-500 group-hover:opacity-55">
                                <span className="h-1 w-8 rounded-full bg-cyan-100"/>
                                <span className="h-1 w-2 rounded-full bg-fuchsia-100"/>
                                <span className="h-1 w-5 rounded-full bg-cyan-100"/>
                            </div>
                        </div>
                    </motion.article>
                ))}
            </div>
        </section>
    );
}
