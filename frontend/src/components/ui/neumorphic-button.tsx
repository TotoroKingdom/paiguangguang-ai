import type { AnchorHTMLAttributes } from "react";

export function NeumorphicButton({ className = "", variant = "primary", ...props }: AnchorHTMLAttributes<HTMLAnchorElement> & { variant?: "primary" | "soft" }) {
  return <a className={`neu-button neu-button--${variant} ${className}`} {...props} />;
}
