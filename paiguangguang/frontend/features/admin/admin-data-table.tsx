"use client";

import type { ReactNode } from "react";

export type AdminDataTableState = "loading" | "ready" | "empty" | "forbidden" | "error";

export type AdminDataTableColumn<T> = {
  key: string;
  header: string;
  render: (row: T) => ReactNode;
  sortable?: boolean;
  sortKey?: string;
  className?: string;
};

export function AdminDataTable<T>({
  columns,
  rows,
  state,
  loadingMessage,
  emptyMessage,
  forbiddenMessage,
  errorMessage,
  sortBy,
  sortOrder,
  onSort,
  getRowKey,
  onRowClick,
  activeRowKey,
}: {
  columns: AdminDataTableColumn<T>[];
  rows: T[];
  state: AdminDataTableState;
  loadingMessage: string;
  emptyMessage: string;
  forbiddenMessage: string;
  errorMessage: string | null;
  sortBy?: string | null;
  sortOrder?: "asc" | "desc";
  onSort?: (sortKey: string) => void;
  getRowKey: (row: T) => string;
  onRowClick?: (row: T) => void;
  activeRowKey?: string | null;
}) {
  if (state === "loading") {
    return <div className="border border-dashed border-ink/15 bg-paper/70 p-4 text-sm">{loadingMessage}</div>;
  }

  if (state === "forbidden") {
    return <div className="border border-clay/20 bg-clay/10 p-4 text-sm">{forbiddenMessage}</div>;
  }

  if (state === "error") {
    return <div className="border border-clay/20 bg-clay/10 p-4 text-sm">{errorMessage ?? emptyMessage}</div>;
  }

  if (state === "empty" || rows.length === 0) {
    return <div className="border border-ink/10 bg-paper/70 p-4 text-sm">{emptyMessage}</div>;
  }

  return (
    <div className="overflow-hidden border border-ink/10 bg-white shadow-sm">
      <table className="w-full border-collapse">
        <thead className="bg-paper/70">
          <tr className="border-b border-ink/10">
            {columns.map((column) => {
              const isSorted = sortBy === column.sortKey;
              const sortLabel = isSorted ? (sortOrder === "asc" ? "ascending" : "descending") : undefined;
              return (
                <th key={column.key} scope="col" className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-clay">
                  {column.sortable && column.sortKey && onSort ? (
                    <button
                      type="button"
                      onClick={() => onSort(column.sortKey ?? column.key)}
                      aria-label={`Sort by ${column.header}`}
                      aria-sort={sortLabel}
                      className="inline-flex items-center gap-1 text-left transition hover:text-ink"
                    >
                      <span>{column.header}</span>
                      <span aria-hidden="true" className="text-[10px]">
                        {isSorted ? (sortOrder === "asc" ? "▲" : "▼") : "↕"}
                      </span>
                    </button>
                  ) : (
                    <span>{column.header}</span>
                  )}
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => {
            const rowKey = getRowKey(row);
            const active = activeRowKey === rowKey;
            return (
              <tr
                key={rowKey}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
                className={[
                  "border-b border-ink/10 transition last:border-b-0",
                  onRowClick ? "cursor-pointer hover:bg-paper/60" : "",
                  active ? "bg-tide/6" : "",
                  index % 2 === 0 ? "" : "bg-white/60",
                ].join(" ")}
              >
                {columns.map((column) => (
                  <td key={column.key} className={["px-4 py-3 text-sm text-ink", column.className ?? ""].join(" ")}>
                    {column.render(row)}
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
