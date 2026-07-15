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
        d="M28.7 11.8c-2.3-1.7-5.1-2.6-8.1-2.6-6.8 0-12.3 5.5-12.3 12.3 0 2.6.8 5 2.1 7l-2.1 4.8 5-1.8c1.7 1.2 3.7 2 6 2 6.8 0 12.3-5.5 12.3-12.3 0-2.9-1-5.5-2.9-7.7l2-5.1-4 1.4Z"
        fill="currentColor"
        opacity="0.18"
      />
      <path
        d="M14.2 23.1c0-4.5 3.6-8.1 8.1-8.1 1.8 0 3.4.6 4.7 1.6l4.1-2.1-1.1 4.4c1 1.4 1.6 3.1 1.6 4.9 0 4.5-3.6 8.1-8.1 8.1-1.6 0-3.1-.5-4.4-1.2l-4.9 1.4 1.8-4.4c-.7-1.2-1.8-3-1.8-4.6Z"
        fill="currentColor"
      />
      <circle cx="24.6" cy="19.7" r="1.3" fill="white" />
      <path
        d="M16.4 28.4c1.8 1.3 4 2 6.4 2 2.8 0 5.2-1 7.1-2.7"
        stroke="white"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
    </svg>
  );
}
