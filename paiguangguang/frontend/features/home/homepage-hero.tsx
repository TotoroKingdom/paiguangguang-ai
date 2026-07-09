"use client";

import {motion} from "framer-motion";

export function HomepageHero() {
    return (
        <section id="hero" className="px-4 sm:px-6 lg:px-8">
            <motion.div
                initial={{opacity: 0, y: 18}}
                animate={{opacity: 1, y: 0}}
                transition={{duration: 0.6, ease: "easeOut"}}
                className="space-y-7 pt-2"
            >
                <div className="mx-auto flex w-full max-w-6xl">
                    <div
                        className="inline-flex items-center gap-2 rounded-full border border-cyan-300/20 bg-cyan-300/8 px-4 py-2 text-sm font-medium text-cyan-100">
                        <span className="h-2 w-2 rounded-full bg-cyan-300"/>
                        Overview
                    </div>
                </div>
                <motion.article
                    initial={{opacity: 0, y: 14}}
                    animate={{opacity: 1, y: 0}}
                    transition={{duration: 0.5, ease: "easeOut", delay: 0.08}}
                    className="rounded-[28px] border border-white/10 bg-white/5 p-5 backdrop-blur-sm w-full max-w-6xl mx-auto"
>
                    <p className="text-xs font-semibold uppercase tracking-[0.3em] text-cyan-200/80">Self
                        Introduction</p>
                    <h2 className="mt-3 text-2xl font-black text-white">TotoroKingdom</h2>
                    <p className="mt-4 text-sm leading-7 text-slate-300">
                        I'm a full-stack AI application developer focused on RAG Engineering, Agent Workflows, and Vibe Coding.
                    </p>
                    <p className="mt-3 text-sm leading-7 text-slate-300">
                        With a Java backend foundation and hands-on experience in FastAPI, Redis, PostgreSQL, vector
                        databases, and LLM applications,
                    </p>
                    <p className="mt-3 text-sm leading-7 text-slate-300">
                        I build practical AI systems that combine retrieval, reasoning, tool calling, and automation.
                    </p>
                    <p className="mt-3 text-sm leading-7 text-slate-300">
                        I believe AI will reshape the future of software, and my goal is to become a RAG Engineer / AI
                        Application Engineer who creates reliable and useful AI products.
                    </p>
                </motion.article>
            </motion.div>
        </section>
    )
        ;
}
