import type { CSSProperties } from "react";

const aliases: Record<string, string> = {
  "file-text": "file",
  "file-search": "file",
  table: "chart",
  target: "spark",
  clipboard: "file",
  "code-review": "code",
  document: "file",
  book: "skill",
  folder: "file",
  users: "agent",
  list: "file",
  compass: "globe",
  terminal: "code",
  brain: "agent",
  "bar-chart": "chart",
  notebook: "skill",
};
const paths: Record<string, string> = {
  search: "m21 21-5-5M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0Z",
  tool: "m14 6 4-4a6 6 0 0 1-7 8L4 19a2 2 0 0 1-3-3l9-7a6 6 0 0 1 8-7l-4 4Z",
  skill: "M12 5C8 2 4 3 2 4v16c4-2 7-1 10 1m0-16c4-3 8-2 10-1v16c-4-2-7-1-10 1V5Z",
  mcp: "M8 2v5m8-5v5M5 7h14v3a7 7 0 0 1-14 0V7Zm7 10v5",
  agent: "M12 2v3M8 2h8M4 8h16v12H4V8ZM1 12v4m22-4v4M8 12v3m8-3v3m-7 3h6",
  file: "M14 2H4v20h16V8l-6-6Zm0 0v6h6M8 13h8m-8 4h5",
  chat: "M21 11a9 9 0 0 1-9 9H6l-4 2 1-6a9 9 0 1 1 18-5Z",
  plus: "M12 4v16M4 12h16",
  send: "M12 20V4m-7 7 7-7 7 7",
  close: "m6 6 12 12M6 18 18 6",
  check: "m5 12 4 4L19 6",
  chevron: "m14 6-6 6 6 6",
  menu: "M4 6h16M4 12h16M4 18h16",
  more: "M4 12h.01M12 12h.01M20 12h.01",
  trash: "M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7m4-7v7",
  settings:
    "M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8ZM12 2v3m0 14v3M2 12h3m14 0h3M5 5l2 2m10 10 2 2M5 19l2-2M17 7l2-2",
  upload: "M12 16V3m-5 5 5-5 5 5M3 15v6h18v-6",
  arrow: "M4 12h16m-6-6 6 6-6 6",
  globe: "M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0ZM3 12h18M12 3c-5 5-5 13 0 18 5-5 5-13 0-18Z",
  database: "M3 6c0-5 18-5 18 0m-18 0c0 5 18 5 18 0M3 6v12c0 5 18 5 18 0V6M3 12c0 5 18 5 18 0",
  code: "m8 7-5 5 5 5m8-10 5 5-5 5m-3-14-2 18",
  chart: "M4 20V12h4v8m2 0V8h4v12m2 0V3h4v17M2 21h20",
  calendar: "M5 4h14v17H5V4Zm3-3v6m8-6v6M5 10h14m-10 4h6m-6 3h4",
  presentation: "M3 4h18v13H3V4Zm9 13v5m-4 0 4-5 4 5M7 8h10m-10 4h6",
  paperclip: "m8 14 7-7a3 3 0 0 1 4 4L9 21a5 5 0 0 1-7-7L13 3a6 6 0 0 1 8 8L10 22",
  stop: "M6 6h12v12H6Z",
  retry: "M3 10a9 9 0 1 1 1 8M3 3v7h7",
  spark: "m12 2 3 7 7 3-7 3-3 7-3-7-7-3 7-3 3-7Z",
};

export function AssistantIcon({
  name,
  size = 22,
  className,
  style,
}: {
  name: string;
  size?: number;
  className?: string;
  style?: CSSProperties;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.65"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      style={style}
      aria-hidden="true"
    >
      <path d={paths[aliases[name] ?? name] ?? paths.spark} />
    </svg>
  );
}
