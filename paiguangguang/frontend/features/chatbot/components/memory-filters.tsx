"use client";

import type { MemoryStatus, MemoryType } from "../types/memory";
import type { MemoryScope, MemoryTypeFilter } from "../hooks/use-memories";

const STATUS_LABELS: Record<MemoryStatus, string> = {
  active: "Active",
  candidate: "Candidate",
  superseded: "Superseded",
};

const MEMORY_TYPE_LABELS: Record<MemoryType, string> = {
  preference: "Preference",
  goal: "Goal",
  project_context: "Project context",
  explicit: "Explicit",
  fact: "Fact",
  work_context: "Work context",
};

type MemoryFiltersProps = {
  status: MemoryStatus;
  memoryType: MemoryTypeFilter;
  scope: MemoryScope;
  conversationScopeAvailable: boolean;
  onChangeStatus: (status: MemoryStatus) => void | Promise<void>;
  onChangeMemoryType: (memoryType: MemoryTypeFilter) => void | Promise<void>;
  onChangeScope: (scope: MemoryScope) => void | Promise<void>;
};

export function MemoryFilters({
  status,
  memoryType,
  scope,
  conversationScopeAvailable,
  onChangeStatus,
  onChangeMemoryType,
  onChangeScope,
}: MemoryFiltersProps) {
  return (
    <section className="rounded-2xl border border-ink/10 bg-white/80 p-4 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-clay">Filters</p>
          <h2 className="mt-1 text-lg font-semibold text-ink">Memory workspace</h2>
        </div>

        {conversationScopeAvailable ? (
          <button
            type="button"
            aria-pressed={scope === "current"}
            onClick={() => void onChangeScope(scope === "current" ? "all" : "current")}
            className={[
              "rounded-full border px-3 py-2 text-sm font-semibold transition",
              scope === "current"
                ? "border-tide/55 bg-tide text-paper shadow-sm"
                : "border-ink/10 bg-paper/70 text-ink hover:border-tide/40 hover:bg-white",
            ].join(" ")}
          >
            Current conversation
          </button>
        ) : null}
      </div>

      <div className="mt-4 grid gap-3 lg:grid-cols-[minmax(0,1fr)_minmax(14rem,auto)]">
        <div className="flex flex-wrap gap-2">
          {(Object.keys(STATUS_LABELS) as MemoryStatus[]).map((nextStatus) => (
            <button
              key={nextStatus}
              type="button"
              aria-pressed={status === nextStatus}
              onClick={() => void onChangeStatus(nextStatus)}
              className={[
                "rounded-full border px-3 py-2 text-sm font-medium transition",
                status === nextStatus
                  ? "border-tide/55 bg-tide text-paper shadow-sm"
                  : "border-ink/10 bg-paper/70 text-ink hover:border-tide/40 hover:bg-white",
              ].join(" ")}
            >
              {STATUS_LABELS[nextStatus]}
            </button>
          ))}
        </div>

        <label className="flex min-w-0 items-center gap-3">
          <span className="shrink-0 text-xs font-semibold uppercase tracking-wide text-ink/50">Memory type</span>
          <select
            aria-label="Memory type"
            value={memoryType}
            onChange={(event) => void onChangeMemoryType(event.target.value as MemoryTypeFilter)}
            className="min-w-0 flex-1 rounded-xl border border-ink/15 bg-white px-3 py-2 text-sm text-ink outline-none transition focus:border-tide/50 focus:ring-2 focus:ring-tide/10"
          >
            <option value="all">All types</option>
            {(Object.keys(MEMORY_TYPE_LABELS) as MemoryType[]).map((type) => (
              <option key={type} value={type}>
                {MEMORY_TYPE_LABELS[type]}
              </option>
            ))}
          </select>
        </label>
      </div>
    </section>
  );
}
