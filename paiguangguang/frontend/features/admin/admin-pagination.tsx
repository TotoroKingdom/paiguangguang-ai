"use client";

function clampPage(totalPages: number, page: number) {
  if (totalPages < 1) {
    return 1;
  }
  return Math.min(Math.max(page, 1), totalPages);
}

export function AdminPagination({
  page,
  pageSize,
  total,
  pageSizeOptions = [5, 10, 20, 50],
  onPageChange,
  onPageSizeChange,
}: {
  page: number;
  pageSize: number;
  total: number;
  pageSizeOptions?: number[];
  onPageChange: (page: number) => void;
  onPageSizeChange: (pageSize: number) => void;
}) {
  const totalPages = Math.max(1, Math.ceil(total / Math.max(pageSize, 1)));
  const currentPage = clampPage(totalPages, page);
  const from = total === 0 ? 0 : (currentPage - 1) * pageSize + 1;
  const to = total === 0 ? 0 : Math.min(currentPage * pageSize, total);

  return (
    <div className="flex flex-col gap-3 border border-ink/10 bg-white px-4 py-3 text-sm text-ink/75 sm:flex-row sm:items-center sm:justify-between">
      <div>
        显示 <span className="font-semibold text-ink">{from}</span> 到{" "}
        <span className="font-semibold text-ink">{to}</span>，共{" "}
        <span className="font-semibold text-ink">{total}</span>
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <label className="flex items-center gap-2">
          <span className="text-xs font-semibold uppercase tracking-wide text-clay">每页条数</span>
          <select
            value={pageSize}
            onChange={(event) => onPageSizeChange(Number(event.target.value))}
            className="border border-ink/15 bg-white px-3 py-2 text-sm text-ink outline-none focus:border-tide/50"
          >
            {pageSizeOptions.map((size) => (
              <option key={size} value={size}>
                {size}
              </option>
            ))}
          </select>
        </label>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => onPageChange(clampPage(totalPages, currentPage - 1))}
            disabled={currentPage <= 1}
            className="border border-ink/15 bg-paper px-3 py-2 text-sm font-semibold text-ink disabled:cursor-not-allowed disabled:opacity-50"
          >
            上一页
          </button>
          <div className="min-w-24 text-center text-xs font-semibold uppercase tracking-wide text-clay">
            第 {currentPage} / {totalPages} 页
          </div>
          <button
            type="button"
            onClick={() => onPageChange(clampPage(totalPages, currentPage + 1))}
            disabled={currentPage >= totalPages}
            className="border border-ink/15 bg-paper px-3 py-2 text-sm font-semibold text-ink disabled:cursor-not-allowed disabled:opacity-50"
          >
            下一页
          </button>
        </div>
      </div>
    </div>
  );
}
