import type { HTMLAttributes } from "react";

export function NeumorphicPanel({ className = "", ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={`neu-surface neu-panel ${className}`} {...props} />;
}
