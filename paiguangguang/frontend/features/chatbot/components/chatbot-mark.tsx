"use client";

type ChatbotMarkProps = {
  className?: string;
};

export function ChatbotMark({ className = "" }: ChatbotMarkProps) {
  return (
    <svg
      viewBox="0 0 40 40"
      aria-hidden="true"
      focusable="false"
      className={className}
      fill="none"
    >
      <circle cx="20" cy="20" r="18" fill="currentColor" opacity="0.08" />
      <path
        d="M13.5 12.5V10.5M26.5 12.5V10.5"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
      <circle cx="13.5" cy="9.5" r="1.6" fill="currentColor" />
      <circle cx="26.5" cy="9.5" r="1.6" fill="currentColor" />
      <rect
        x="10.5"
        y="12"
        width="19"
        height="16"
        rx="8"
        stroke="currentColor"
        strokeWidth="1.8"
      />
      <circle cx="16" cy="19" r="1.5" fill="currentColor" />
      <circle cx="24" cy="19" r="1.5" fill="currentColor" />
      <path
        d="M16.5 23.5c1.4 1.2 5.6 1.2 7 0"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
      <path
        d="M15.5 29.5h9"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        opacity="0.55"
      />
    </svg>
  );
}
