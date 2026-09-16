"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { motion } from "framer-motion";

import type { RagFlowStep } from "./homepage-data";

type RagFlowVisualProps = {
  ingestionSteps: RagFlowStep[];
  querySteps: RagFlowStep[];
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

const fallbackStep = (id: string, title: string, description: string, kind: RagFlowStep["kind"]): RagFlowStep => ({
  id,
  title,
  description,
  kind
});

const kindLabels: Record<RagFlowStep["kind"], string> = {
  ingestion: "ingest",
  query: "query",
  branch: "branch",
  system: "system",
  ai: "model",
  storage: "storage",
  response: "output"
};

function FlowNode({ step, order, emphasis = false }: { step: RagFlowStep; order: number; emphasis?: boolean }) {
  return (
    <motion.article
      initial={{ opacity: 0, y: 8 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.2 }}
      transition={{ duration: 0.28, delay: Math.min(order * 0.018, 0.25) }}
      className={`flow-node ${emphasis ? "flow-node--emphasis" : ""}`}
    >
      <div className="flow-node__top">
        <span className="flow-node__kind">{kindLabels[step.kind]}</span>
        <span className="flow-node__order">{String(order).padStart(2, "0")}</span>
      </div>
      <h3 className="flow-node__title">{step.title}</h3>
      <p className="flow-node__description">{step.description}</p>
    </motion.article>
  );
}

function FlowSequence({ steps, startOrder }: { steps: RagFlowStep[]; startOrder: number }) {
  const rows: RagFlowStep[][] = [];

  for (let index = 0; index < steps.length; index += 4) {
    rows.push(steps.slice(index, index + 4));
  }

  return (
    <div className="flow-sequence">
      {rows.map((row, rowIndex) => (
        <div key={`${row[0]?.id ?? "row"}-${rowIndex}`} className="flow-sequence__row">
          {row.map((step, index) => (
            <div key={step.id} className="flow-sequence__item">
              <FlowNode step={step} order={startOrder + rowIndex * 4 + index} />
              {index < row.length - 1 ? <span className="flow-connector" aria-hidden="true" /> : null}
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

function LaneHeader({ index, title, copy, status }: { index: string; title: string; copy: string; status: string }) {
  return (
    <div className="flow-lane__header">
      <div>
        <div className="flow-lane__heading">
          <span className="flow-lane__index">{index}</span>
          <p className="flow-lane__title">{title}</p>
        </div>
        <p className="flow-lane__copy">{copy}</p>
      </div>
      <span className="flow-lane__status">{status}</span>
    </div>
  );
}

function FlowBranch({ steps, permissionStep }: { steps: RagFlowStep[]; permissionStep: RagFlowStep }) {
  return (
    <div className="flow-query__branch">
      <p className="flow-branch__label">Parallel retrieval</p>
      <div className="flow-branch__nodes">
        {steps.map((step, index) => (
          <FlowNode key={step.id} step={step} order={index + 7} />
        ))}
      </div>
      <div className="flow-query__permission">
        <FlowNode step={permissionStep} order={9} />
      </div>
    </div>
  );
}

export function RagFlowVisual({ ingestionSteps, querySteps }: RagFlowVisualProps) {
  const boardRef = useRef<HTMLDivElement>(null);
  const [particlesActive, setParticlesActive] = useState(false);

  useEffect(() => {
    const board = boardRef.current;
    if (!board) return;

    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (prefersReducedMotion || !("IntersectionObserver" in window)) return;

    const observer = new IntersectionObserver(
      ([entry]) => setParticlesActive(entry.isIntersecting),
      { threshold: 0.18 }
    );

    observer.observe(board);
    return () => observer.disconnect();
  }, []);

  const queryMainSteps = useMemo(() => {
    const userQuestion = querySteps.find((step) => step.id === "user-question");
    const inputGuardrails = querySteps.find((step) => step.id === "input-guardrails");
    const rewrite = querySteps.find((step) => step.id === "rewrite");

    return [
      userQuestion ?? fallbackStep("user-question", "用户问题", "用户提出问题，系统保留原始 query 用于追踪。", "query"),
      inputGuardrails ?? fallbackStep("input-guardrails", "输入护栏", "检测越权意图、PII 和明显无效输入。", "system"),
      lightweightRewriteStep,
      rewrite ?? fallbackStep("rewrite", "Query Rewrite", "补全上下文并生成更适合召回的 query。", "query")
    ];
  }, [querySteps]);

  const hybridStep = useMemo(
    () => querySteps.find((step) => step.id === "hybrid-retrieval") ?? fallbackStep("hybrid-retrieval", "Hybrid Retrieval", "分叉为 BM25 和 Vector 两条召回路线。", "branch"),
    [querySteps]
  );

  const permissionStep = useMemo(
    () => querySteps.find((step) => step.id === "permission-filter") ?? fallbackStep("permission-filter", "权限过滤", "结合 workspace 和 metadata 过滤候选结果。", "system"),
    [querySteps]
  );

  const afterRetrievalSteps = useMemo(() => {
    const order = ["rrf", "top50", "rerank", "context", "llm", "citation"];

    return order
      .map((id) => querySteps.find((step) => step.id === id))
      .filter((step): step is RagFlowStep => step !== undefined)
      .map((step) => (step.id === "citation"
        ? { ...step, id: "response", title: "Response / Citation", description: "输出最终回答、来源文档、chunk 信息和可检查引用。", kind: "response" as const }
        : step));
  }, [querySteps]);

  const ingestionFlowSteps = ingestionSteps.slice(0, 8);
  const branchSteps = [bm25RetrievalStep, vectorRetrievalStep];

  return (
    <motion.div
      ref={boardRef}
      initial={{ opacity: 0, y: 14 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.15 }}
      transition={{ duration: 0.45, ease: "easeOut" }}
      className="surface flow-surface"
    >
      <div className="flow-surface__header">
        <div>
          <p className="eyebrow">RAG control plane</p>
          <h3 className="flow-surface__title">可观测的 RAG 链路</h3>
        </div>
        <div className="flow-surface__meta">
          <span className={`flow-pulse ${particlesActive ? "flow-pulse--active" : ""}`} />
          live map / traceable
        </div>
      </div>

      <div className="flow-content">
        <section className="flow-lane">
          <LaneHeader index="01" title="Document ingestion" copy="从原始文档到可检索的向量与 metadata。" status="background jobs" />
          <FlowSequence steps={ingestionFlowSteps} startOrder={1} />
        </section>

        <section className="flow-lane">
          <LaneHeader index="02" title="Query runtime" copy="从用户问题到候选上下文，保留每个决策节点。" status="request path" />
          <div className="flow-query">
            <div className="flow-query__primary">
              {queryMainSteps.map((step, index) => (
                <div key={step.id} className="flow-sequence__item">
                  <FlowNode step={step} order={index + 1} />
                  {index < queryMainSteps.length - 1 ? <span className="flow-connector" aria-hidden="true" /> : null}
                </div>
              ))}
            </div>
            <div className="flow-query__hybrid">
              <FlowNode step={hybridStep} order={6} />
            </div>
            <FlowBranch steps={branchSteps} permissionStep={permissionStep} />
          </div>
        </section>

        <section className="flow-lane">
          <LaneHeader index="03" title="Answer pipeline" copy="融合、精排、组装上下文，并输出带引用的回答。" status="guarded output" />
          <div className="flow-post">
            {afterRetrievalSteps.map((step, index) => (
              <FlowNode key={step.id} step={step} order={index + 10} emphasis={step.id === "response"} />
            ))}
          </div>
        </section>
      </div>
    </motion.div>
  );
}
