import type { SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement> & {
  size?: number;
};

function createIconProps({ size = 18, ...props }: IconProps) {
  return {
    "aria-hidden": true,
    fill: "none",
    height: size,
    stroke: "currentColor",
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    strokeWidth: 1.8,
    viewBox: "0 0 24 24",
    width: size,
    ...props
  };
}

export function ArrowUpRightIcon(props: IconProps) {
  return (
    <svg {...createIconProps(props)}>
      <path d="M7 17 17 7" />
      <path d="M7 7h10v10" />
    </svg>
  );
}

export function ActivityIcon(props: IconProps) {
  return (
    <svg {...createIconProps(props)}>
      <path d="M3 12h4l2.2-7 4.2 14L16 12h5" />
    </svg>
  );
}

export function BotIcon(props: IconProps) {
  return (
    <svg {...createIconProps(props)}>
      <rect x="4" y="7" width="16" height="12" rx="3" />
      <path d="M12 3v4M8 12h.01M16 12h.01M8 16h8" />
    </svg>
  );
}

export function CodeIcon(props: IconProps) {
  return (
    <svg {...createIconProps(props)}>
      <path d="m8 8-4 4 4 4M16 8l4 4-4 4M14 4l-4 16" />
    </svg>
  );
}

export function DatabaseIcon(props: IconProps) {
  return (
    <svg {...createIconProps(props)}>
      <ellipse cx="12" cy="5" rx="7" ry="3" />
      <path d="M5 5v7c0 1.66 3.13 3 7 3s7-1.34 7-3V5M5 12v7c0 1.66 3.13 3 7 3s7-1.34 7-3v-7" />
    </svg>
  );
}

export function GithubIcon(props: IconProps) {
  return (
    <svg {...createIconProps(props)}>
      <path d="M15 22v-3.5c.04-1-.3-1.75-.95-2.5 3.1-.35 6.35-1.55 6.35-7A5.5 5.5 0 0 0 19 5.2 5.1 5.1 0 0 0 18.9 1S17.7.65 15 2.45a13.5 13.5 0 0 0-6 0C6.3.65 5.1 1 5.1 1A5.1 5.1 0 0 0 5 5.2a5.5 5.5 0 0 0-1.4 3.8c0 5.45 3.25 6.65 6.35 7-.65.75-.99 1.5-.95 2.5V22" />
      <path d="M9 18c-3.5 1.5-3.5-1.5-5-1.5" />
    </svg>
  );
}

export function LayersIcon(props: IconProps) {
  return (
    <svg {...createIconProps(props)}>
      <path d="m12 3 9 5-9 5-9-5 9-5Z" />
      <path d="m3 12 9 5 9-5M3 16l9 5 9-5" />
    </svg>
  );
}

export function MailIcon(props: IconProps) {
  return (
    <svg {...createIconProps(props)}>
      <rect x="3" y="5" width="18" height="14" rx="2" />
      <path d="m3 7 9 6 9-6" />
    </svg>
  );
}

export function WorkflowIcon(props: IconProps) {
  return (
    <svg {...createIconProps(props)}>
      <rect x="3" y="3" width="6" height="6" rx="1.5" />
      <rect x="15" y="15" width="6" height="6" rx="1.5" />
      <rect x="15" y="3" width="6" height="6" rx="1.5" />
      <path d="M9 6h6M18 9v6M15 18H9V9" />
    </svg>
  );
}
