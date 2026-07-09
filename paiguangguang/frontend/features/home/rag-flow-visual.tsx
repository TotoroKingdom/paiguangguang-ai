"use client";

import {useEffect, useMemo, useRef, useState, type ReactNode} from "react";
import {motion} from "framer-motion";

import type {RagFlowStep} from "./homepage-data";

type RagFlowVisualProps = {
    ingestionSteps: RagFlowStep[];
    querySteps: RagFlowStep[];
};

const kindStyles: Record<RagFlowStep["kind"], string> = {
    ingestion: "border-emerald-400/30 bg-emerald-400/10 text-emerald-100",
    query: "border-sky-400/30 bg-sky-400/10 text-sky-100",
    branch: "border-fuchsia-400/30 bg-fuchsia-400/10 text-fuchsia-100",
    system: "border-amber-400/30 bg-amber-400/10 text-amber-100",
    ai: "border-violet-400/30 bg-violet-400/10 text-violet-100",
    storage: "border-slate-200/30 bg-slate-200/10 text-slate-100",
    response: "border-slate-200/30 bg-slate-200/10 text-slate-100"
};

const NODE_SIZE = 154;
// 从左到右卡片间距拉大，避免右侧空白太明显
const COL_GAP = 100;
const ROW_GAP = 48;
const COL_STEP = NODE_SIZE + COL_GAP;
const ROW_STEP = NODE_SIZE + ROW_GAP;
const BOARD_WIDTH = NODE_SIZE * 8 + COL_GAP * 7;
const BOARD_HEIGHT = NODE_SIZE * 5 + ROW_GAP * 4;
const userAvatarStep: RagFlowStep = {
    id: "user-avatar",
    title: "用户",
    description: "提出问题，并接收最终回答。",
    kind: "query"
};

const lightweightRewriteStep: RagFlowStep = {
    id: "lightweight-llm-rewrite",
    title: "轻型 LLM 改写",
    description: "使用轻量模型理解问题意图，生成更适合检索的 query。",
    kind: "ai"
};

const bm25RetrievalStep: RagFlowStep = {
    id: "bm25-retrieval",
    title: "BM25 关键词召回",
    description: "基于关键词、倒排索引和精确匹配召回候选 chunk。",
    kind: "branch"
};

const vectorRetrievalStep: RagFlowStep = {
    id: "vector-retrieval",
    title: "Vector 向量召回",
    description: "将改写后的 query 向量化，召回语义相似 chunk。",
    kind: "branch"
};

const milvusHubStep: RagFlowStep = {
    id: "milvus-hub",
    title: "Milvus 向量库",
    description: "合并多路召回结果，返回候选 chunk 集合。",
    kind: "storage"
};

const outputGuardrailsStep: RagFlowStep = {
    id: "output-guardrails",
    title: "输出护栏",
    description: "检查回答安全性、引用完整性和输出格式。",
    kind: "system"
};

const finalAnswerStep: RagFlowStep = {
    id: "final-answer",
    title: "最终回答",
    description: "把通过输出护栏的回答返回给用户，完成一次问答闭环。",
    kind: "response"
};

function formatOrder(order: number) {
    return String(order).padStart(2, "0");
}

function OrderBadge({order}: { order: number }) {
    return (
        <span
            className="rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-300">
            {formatOrder(order)}
        </span>
    );
}

function center(col: number, row: number) {
    return {
        x: NODE_SIZE / 2 + (col - 1) * COL_STEP,
        y: NODE_SIZE / 2 + (row - 1) * ROW_STEP
    };
}

function right(col: number, row: number) {
    const p = center(col, row);
    return {x: p.x + NODE_SIZE / 2, y: p.y};
}

function left(col: number, row: number) {
    const p = center(col, row);
    return {x: p.x - NODE_SIZE / 2, y: p.y};
}

function top(col: number, row: number) {
    const p = center(col, row);
    return {x: p.x, y: p.y - NODE_SIZE / 2};
}

function bottom(col: number, row: number) {
    const p = center(col, row);
    return {x: p.x, y: p.y + NODE_SIZE / 2};
}

function line(from: { x: number; y: number }, to: { x: number; y: number }) {
    return `M ${from.x} ${from.y} L ${to.x} ${to.y}`;
}

function curve(from: { x: number; y: number }, to: { x: number; y: number }) {
    const midX = (from.x + to.x) / 2;

    return `M ${from.x} ${from.y} C ${midX} ${from.y}, ${midX} ${to.y}, ${to.x} ${to.y}`;
}

function FlowBoardConnectors({particlesActive}: { particlesActive: boolean }) {
    const BRANCH_PULL = 48;

    function branchTopRight() {
        const p = right(7, 2);
        return {
            x: p.x,
            y: p.y + BRANCH_PULL
        };
    }

    function branchTopLeft() {
        const p = left(7, 2);
        return {
            x: p.x,
            y: p.y + BRANCH_PULL
        };
    }

    function branchBottomRight() {
        const p = right(7, 4);
        return {
            x: p.x,
            y: p.y - BRANCH_PULL
        };
    }

    function branchBottomLeft() {
        const p = left(7, 4);
        return {
            x: p.x,
            y: p.y - BRANCH_PULL
        };
    }

    const paths = [
        // 文档入库链路：1 -> 8
        {id: "doc-1-2", d: line(right(1, 1), left(2, 1))},
        {id: "doc-2-3", d: line(right(2, 1), left(3, 1))},
        {id: "doc-3-4", d: line(right(3, 1), left(4, 1))},
        {id: "doc-4-5", d: line(right(4, 1), left(5, 1))},
        {id: "doc-5-6", d: line(right(5, 1), left(6, 1))},
        {id: "doc-6-7", d: line(right(6, 1), left(7, 1))},
        {id: "doc-7-8", d: line(right(7, 1), left(8, 1))},

        // 文档入库 8 -> 用户问答 09
        {id: "doc-8-to-query-09", d: line(bottom(8, 1), top(8, 3))},

        // 用户问答主链路：01 -> 06
        {id: "query-01-02", d: line(right(1, 3), left(2, 3))},
        {id: "query-02-03", d: line(right(2, 3), left(3, 3))},
        {id: "query-03-04", d: line(right(3, 3), left(4, 3))},
        {id: "query-04-05", d: line(right(4, 3), left(5, 3))},
        {id: "query-05-06", d: line(right(5, 3), left(6, 3))},

        // 06 分叉到 07 / 08
        {id: "query-06-07", d: curve(right(6, 3), branchTopLeft())},
        {id: "query-06-08", d: curve(right(6, 3), branchBottomLeft())},

        {id: "query-07-09", d: curve(branchTopRight(), left(8, 3))},
        {id: "query-08-09", d: curve(branchBottomRight(), left(8, 3))},
        // 09 向下进入后处理
        {id: "query-09-10", d: line(bottom(8, 3), top(8, 5))},

        // 10 -> 17 从右向左
        {id: "query-10-11", d: line(left(8, 5), right(7, 5))},
        {id: "query-11-12", d: line(left(7, 5), right(6, 5))},
        {id: "query-12-13", d: line(left(6, 5), right(5, 5))},
        {id: "query-13-14", d: line(left(5, 5), right(4, 5))},
        {id: "query-14-15", d: line(left(4, 5), right(3, 5))},
        {id: "query-15-16", d: line(left(3, 5), right(2, 5))},
        {id: "query-16-17", d: line(left(2, 5), right(1, 5))},

        // 17 回到 01
        {id: "query-17-01", d: line(top(1, 5), bottom(1, 3))}
    ];

    return (
        <svg
            className="pointer-events-none absolute inset-0 z-0 overflow-visible"
            width={BOARD_WIDTH}
            height={BOARD_HEIGHT}
            viewBox={`0 0 ${BOARD_WIDTH} ${BOARD_HEIGHT}`}
            fill="none"
        >
            <defs>
                <linearGradient id="flow-line-gradient" x1="0" y1="0" x2="1" y2="0">
                    <stop offset="0%" stopColor="rgba(103,232,249,0.2)"/>
                    <stop offset="50%" stopColor="rgba(103,232,249,0.85)"/>
                    <stop offset="100%" stopColor="rgba(217,70,239,0.75)"/>
                </linearGradient>

                <marker
                    id="flow-arrow"
                    markerWidth="8"
                    markerHeight="8"
                    refX="7"
                    refY="4"
                    orient="auto"
                    markerUnits="strokeWidth"
                >
                    <path d="M 0 0 L 8 4 L 0 8 z" fill="rgba(103,232,249,0.8)"/>
                </marker>

                <filter id="flow-glow" x="-50%" y="-50%" width="200%" height="200%">
                    <feGaussianBlur stdDeviation="2.4" result="blur"/>
                    <feMerge>
                        <feMergeNode in="blur"/>
                        <feMergeNode in="SourceGraphic"/>
                    </feMerge>
                </filter>
            </defs>

            {paths.map((path, index) => (
                <g key={path.id}>
                    <path
                        id={path.id}
                        d={path.d}
                        stroke="rgba(103,232,249,0.22)"
                        strokeWidth="2.2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        markerEnd="url(#flow-arrow)"
                    />
                    <path
                        d={path.d}
                        stroke="url(#flow-line-gradient)"
                        strokeWidth={particlesActive ? "2.8" : "2.4"}
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        markerEnd="url(#flow-arrow)"
                        filter="url(#flow-glow)"
                        opacity={0.72 + (index % 3) * 0.08}
                        strokeDasharray={particlesActive ? "12 18" : undefined}
                    >
                        {particlesActive ? (
                            <animate
                                attributeName="stroke-dashoffset"
                                from="60"
                                to="0"
                                dur="2.4s"
                                repeatCount="indefinite"
                                begin={`${(index % 6) * 0.08}s`}
                            />
                        ) : null}
                    </path>
                    {particlesActive ? (
                        <circle
                            r="4.5"
                            fill="rgba(207,250,254,0.98)"
                            filter="url(#flow-glow)"
                            opacity="0.95"
                        >
                            <animateMotion
                                dur="2.4s"
                                repeatCount="indefinite"
                                begin={`${(index % 5) * 0.22}s`}
                            >
                                <mpath href={`#${path.id}`}/>
                            </animateMotion>
                        </circle>
                    ) : null}
                </g>
            ))}
        </svg>
    );
}

function SquareNode({
                        step,
                        index,
                        order
                    }: {
    step: RagFlowStep;
    index: number;
    order?: number;
}) {
    return (
        <motion.div
            initial={{opacity: 0, y: 14}}
            whileInView={{opacity: 1, y: 0}}
            viewport={{once: true, amount: 0.2}}
            transition={{duration: 0.42, delay: index * 0.025}}
            className="group relative z-10 flex aspect-square w-full max-w-[154px] flex-col justify-between rounded-2xl border border-white/10 bg-slate-950/85 p-3.5 shadow-[0_18px_45px_rgba(2,6,23,0.3)] backdrop-blur-sm transition hover:-translate-y-1 hover:border-cyan-300/30 hover:bg-slate-900/90"
        >
            <div className="flex items-center justify-between gap-2">
                <span
                    className={`rounded-full border px-2 py-0.5 text-[9px] font-semibold uppercase tracking-[0.12em] ${kindStyles[step.kind]}`}
                >
                    {step.kind}
                </span>

                {order ? (
                    <OrderBadge order={order}/>
                ) : (
                    <span className="text-[10px] font-medium uppercase tracking-[0.2em] text-slate-400">
                        {String(index + 1).padStart(2, "0")}
                    </span>
                )}
            </div>

            <div>
                <h5 className="text-[14px] font-semibold leading-5 text-white transition group-hover:text-cyan-100">
                    {step.title}
                </h5>

                <p className="mt-2 text-[11px] leading-5 text-slate-300">
                    {step.description}
                </p>
            </div>
        </motion.div>
    );
}

function UserAvatar() {
    return (
        <div className="relative mx-auto h-14 w-14">
            <div
                className="absolute inset-0 rounded-[22px] bg-gradient-to-br from-cyan-300 via-sky-400 to-fuchsia-300 shadow-[0_0_34px_rgba(56,189,248,0.35)]"/>
            <div className="absolute inset-[5px] rounded-[18px] bg-slate-950/85"/>
            <div
                className="absolute left-1/2 top-[11px] h-8 w-8 -translate-x-1/2 rounded-full bg-gradient-to-br from-slate-100 to-cyan-100"/>
            <div className="absolute left-[20px] top-[24px] h-1.5 w-1.5 rounded-full bg-slate-950"/>
            <div className="absolute right-[20px] top-[24px] h-1.5 w-1.5 rounded-full bg-slate-950"/>
            <div className="absolute left-1/2 top-[32px] h-1 w-4 -translate-x-1/2 rounded-full bg-slate-500/70"/>
            <div className="absolute bottom-[9px] left-1/2 h-4 w-8 -translate-x-1/2 rounded-t-full bg-cyan-300/30"/>
            <div className="absolute -right-1 top-[18px] h-5 w-2 rounded-full bg-fuchsia-300/80"/>
            <div className="absolute -left-1 top-[18px] h-5 w-2 rounded-full bg-cyan-300/80"/>
        </div>
    );
}

function UserNode({order}: { order: number }) {
    return (
        <motion.div
            initial={{opacity: 0, y: 14}}
            whileInView={{opacity: 1, y: 0}}
            viewport={{once: true, amount: 0.2}}
            transition={{duration: 0.42}}
            className="relative z-10 flex aspect-square w-full max-w-[154px] flex-col justify-between rounded-2xl border border-cyan-300/25 bg-[radial-gradient(circle_at_top,rgba(56,189,248,0.18),transparent_42%),linear-gradient(180deg,rgba(15,23,42,0.9),rgba(2,6,23,0.96))] p-3.5 text-center shadow-[0_18px_45px_rgba(2,6,23,0.3)] backdrop-blur-sm transition hover:-translate-y-1 hover:border-cyan-300/40"
        >
            <div className="flex justify-end">
                <OrderBadge order={order}/>
            </div>

            <div>
                <UserAvatar/>

                <h5 className="mt-3 text-[14px] font-semibold leading-5 text-white">
                    {userAvatarStep.title}
                </h5>

                <p className="mt-2 text-[11px] leading-5 text-slate-300">
                    {userAvatarStep.description}
                </p>
            </div>
        </motion.div>
    );
}

function DiamondNode({
                         step,
                         order
                     }: {
    step: RagFlowStep;
    order: number;
}) {
    return (
        <motion.div
            initial={{opacity: 0, scale: 0.92, y: 14}}
            whileInView={{opacity: 1, scale: 1, y: 0}}
            viewport={{once: true, amount: 0.25}}
            transition={{duration: 0.45}}
            className="relative z-10 mx-auto flex h-[180px] w-[180px] items-center justify-center"
        >
            <div
                className="flex aspect-square w-[142px] rotate-45 items-center justify-center rounded-2xl border border-fuchsia-300/35 bg-fuchsia-400/10 shadow-[0_0_55px_rgba(217,70,239,0.18)] backdrop-blur-sm">
                <div className="-rotate-45 px-3 text-center">
                    <div className="mb-1 flex justify-center">
                        <OrderBadge order={order}/>
                    </div>

                    <p className="text-[9px] font-semibold uppercase tracking-[0.18em] text-fuchsia-100/80">
                        Branch
                    </p>

                    <h5 className="mt-1 text-sm font-black leading-5 text-white">
                        {step.title}
                    </h5>

                    <p className="mt-1 text-[10px] leading-4 text-slate-300">
                        BM25 / Vector
                    </p>
                </div>
            </div>
        </motion.div>
    );
}

function StripNode({
                       step,
                       order
                   }: {
    step: RagFlowStep;
    order: number;
}) {
    return (
        <motion.div
            initial={{opacity: 0, y: 14}}
            whileInView={{opacity: 1, y: 0}}
            viewport={{once: true, amount: 0.25}}
            transition={{duration: 0.42}}
            className="relative z-10 flex min-h-[88px] w-full max-w-[154px] items-center rounded-2xl border border-fuchsia-300/25 bg-slate-950/85 px-4 py-4 shadow-[0_18px_45px_rgba(2,6,23,0.3)] backdrop-blur-sm transition hover:-translate-y-1 hover:border-fuchsia-300/40"
        >
            <div className="w-full">
                <div className="mb-2 flex items-center justify-between gap-3">
                    <div
                        className="inline-flex rounded-full border border-fuchsia-300/25 bg-fuchsia-400/10 px-2 py-0.5 text-[9px] font-semibold uppercase tracking-[0.16em] text-fuchsia-100">
                        retrieval
                    </div>

                    <OrderBadge order={order}/>
                </div>

                <h5 className="text-sm font-semibold leading-5 text-white">
                    {step.title}
                </h5>

                <p className="mt-1 text-[11px] leading-5 text-slate-300">
                    {step.description}
                </p>
            </div>
        </motion.div>
    );
}

function MilvusNode({order}: { order: number }) {
    return (
        <motion.div
            initial={{opacity: 0, scale: 0.92, y: 14}}
            whileInView={{opacity: 1, scale: 1, y: 0}}
            viewport={{once: true, amount: 0.25}}
            transition={{duration: 0.45}}
            className="relative z-10 flex aspect-square w-full max-w-[154px] flex-col justify-between rounded-2xl border border-cyan-300/30 bg-[radial-gradient(circle_at_top,rgba(56,189,248,0.26),transparent_34%),radial-gradient(circle_at_bottom,rgba(217,70,239,0.18),transparent_38%),linear-gradient(180deg,rgba(15,23,42,0.98),rgba(2,6,23,0.98))] p-3.5 text-center shadow-[0_0_70px_rgba(56,189,248,0.22)] backdrop-blur-sm transition hover:-translate-y-1 hover:border-cyan-300/45"
        >
            <div className="flex justify-end">
                <OrderBadge order={order}/>
            </div>

            <div>
                <p className="text-[9px] font-semibold uppercase tracking-[0.18em] text-cyan-200/80">
                    Vector Store
                </p>

                <h4 className="mt-2 text-[15px] font-black leading-5 text-white">
                    Milvus
                </h4>
            </div>

            <p className="text-[11px] leading-5 text-slate-300">
                {milvusHubStep.description}
            </p>
        </motion.div>
    );
}

function FlowCell({
                      col,
                      row,
                      children
                  }: {
    col: number;
    row: number;
    children: ReactNode;
}) {
    return (
        <div
            className="relative z-10 flex items-center justify-center"
            style={{
                gridColumn: `${col}`,
                gridRow: `${row}`
            }}
        >
            {children}
        </div>
    );
}

function LaneLabel({
                       row,
                       children
                   }: {
    row: number;
    children: ReactNode;
}) {
    return (
        <div
            className="pointer-events-none absolute left-0 z-20 rounded-full border border-white/10 bg-slate-950/80 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.24em] text-cyan-100 shadow-[0_12px_30px_rgba(2,6,23,0.35)]"
            style={{
                top: (row - 1) * ROW_STEP - 20
            }}
        >
            {children}
        </div>
    );
}

export function RagFlowVisual({ingestionSteps, querySteps}: RagFlowVisualProps) {
    const boardRef = useRef<HTMLDivElement>(null);
    const [particlesActive, setParticlesActive] = useState(false);

    useEffect(() => {
        const board = boardRef.current;
        if (!board) {
            return;
        }

        const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
        if (prefersReducedMotion || !("IntersectionObserver" in window)) {
            return;
        }

        const observer = new IntersectionObserver(
            ([entry]) => {
                setParticlesActive(entry.isIntersecting);
            },
            {threshold: 0.18}
        );

        observer.observe(board);

        return () => observer.disconnect();
    }, []);

    const ingestionFlowSteps = useMemo(
        () => ingestionSteps.slice(0, 8),
        [ingestionSteps]
    );

    const inputGuardrailsStep = useMemo(
        () => querySteps.find((step) => step.id === "input-guardrails"),
        [querySteps]
    );

    const userQuestionStep = useMemo(
        () => querySteps.find((step) => step.id === "user-question"),
        [querySteps]
    );

    const rewriteStep = useMemo(
        () => querySteps.find((step) => step.id === "rewrite"),
        [querySteps]
    );

    const hybridStep = useMemo(
        () =>
            querySteps.find((step) => step.id === "hybrid-retrieval") ?? {
                id: "hybrid-retrieval",
                title: "Hybrid Retrieval",
                description: "分叉为 BM25 和 Vector 两条召回路线。",
                kind: "branch" as const
            },
        [querySteps]
    );

    const queryMainSteps = useMemo(
        () =>
            [
                inputGuardrailsStep,
                userQuestionStep,
                lightweightRewriteStep,
                rewriteStep
            ].filter((step): step is RagFlowStep => step !== undefined),
        [inputGuardrailsStep, rewriteStep, userQuestionStep]
    );

    const afterRetrievalSteps = useMemo(() => {
        const order = ["rrf", "top50", "rerank", "context", "llm", "citation"];

        return order
            .map((id) => querySteps.find((step) => step.id === id))
            .filter((step): step is RagFlowStep => step !== undefined)
            .map((step) => {
                if (step.id !== "citation") {
                    return step;
                }

                return {
                    ...step,
                    id: "response",
                    title: "Response / Citation",
                    description: "输出最终回答、来源文档、chunk 信息和可检查引用。"
                };
            });
    }, [querySteps]);

    return (
        <motion.div
            initial={{opacity: 0, scale: 0.97, y: 24}}
            animate={{opacity: 1, scale: 1, y: 0}}
            transition={{duration: 0.7, ease: "easeOut"}}
            className="relative overflow-hidden rounded-[32px] border border-white/10 bg-[radial-gradient(circle_at_top,rgba(56,189,248,0.16),transparent_32%),radial-gradient(circle_at_right,rgba(217,70,239,0.16),transparent_36%),linear-gradient(180deg,rgba(15,23,42,0.95),rgba(2,6,23,0.98))] p-5 shadow-[0_30px_80px_rgba(2,6,23,0.45)]"
        >
            <div
                className="pointer-events-none absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.05)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.05)_1px,transparent_1px)] bg-[size:24px_24px] opacity-20"/>

            <div className="relative space-y-7">
                <div className="flex justify-center text-center">
                    <div>
                        <p className="text-xs font-semibold uppercase tracking-[0.4em] text-cyan-200/80">
                            RAG Control Plane
                        </p>

                        <h3 className="mt-2 text-2xl font-black text-white sm:text-3xl">
                            RAG-链路
                        </h3>
                    </div>

                </div>

                <section className="relative z-10 rounded-[28px] border border-white/10 bg-white/[0.035] p-5 sm:p-6">


                    <div className="w-full overflow-x-auto pb-4">
                        <div
                            ref={boardRef}
                            className="relative grid min-w-full shrink-0"
                            style={{
                                width: BOARD_WIDTH,
                                height: BOARD_HEIGHT,
                                gridTemplateColumns: `repeat(8, ${NODE_SIZE}px)`,
                                gridTemplateRows: `repeat(5, ${NODE_SIZE}px)`,
                                columnGap: COL_GAP,
                                rowGap: ROW_GAP
                            }}
                        >
                            <FlowBoardConnectors particlesActive={particlesActive}/>

                            {/*<LaneLabel row={1}>Document Ingestion</LaneLabel>*/}
                            {/*<LaneLabel row={3}>Query Runtime</LaneLabel>*/}
                            {/*<LaneLabel row={5}>Answer Pipeline</LaneLabel>*/}

                            {ingestionFlowSteps.map((step, index) => (
                                <FlowCell key={step.id} col={index + 1} row={1}>
                                    <SquareNode
                                        step={step}
                                        index={index}
                                        order={index + 1}
                                    />
                                </FlowCell>
                            ))}

                            <FlowCell col={1} row={3}>
                                <UserNode order={1}/>
                            </FlowCell>

                            {queryMainSteps.map((step, index) => (
                                <FlowCell
                                    key={step.id}
                                    col={index + 2}
                                    row={3}
                                >
                                    <SquareNode
                                        step={step}
                                        index={index + 1}
                                        order={index + 2}
                                    />
                                </FlowCell>
                            ))}

                            <FlowCell col={6} row={3}>
                                <DiamondNode step={hybridStep} order={6}/>
                            </FlowCell>

                            <FlowCell col={7} row={2}>
                                <div className="translate-y-12">
                                    <StripNode step={bm25RetrievalStep} order={7}/>
                                </div>
                            </FlowCell>

                            <FlowCell col={7} row={4}>
                                <div className="-translate-y-12">
                                    <StripNode step={vectorRetrievalStep} order={8}/>
                                </div>
                            </FlowCell>

                            <FlowCell col={8} row={3}>
                                <MilvusNode order={9}/>
                            </FlowCell>

                            {afterRetrievalSteps.map((step, index) => (
                                <FlowCell
                                    key={step.id}
                                    col={8 - index}
                                    row={5}
                                >
                                    <SquareNode
                                        step={step}
                                        index={index + 9}
                                        order={index + 10}
                                    />
                                </FlowCell>
                            ))}

                            <FlowCell col={2} row={5}>
                                <SquareNode
                                    step={outputGuardrailsStep}
                                    index={16}
                                    order={16}
                                />
                            </FlowCell>

                            <FlowCell col={1} row={5}>
                                <SquareNode
                                    step={finalAnswerStep}
                                    index={17}
                                    order={17}
                                />
                            </FlowCell>
                        </div>
                    </div>
                </section>

            </div>
        </motion.div>
    );
}
