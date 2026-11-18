import React from "react";

const TONES = {
  neutral: "bg-ink-900/5 text-ink-700",
  brand: "bg-brand-50 text-brand-700",
  info: "bg-sky-50 text-sky-700",
  low: "bg-risk-low-bg text-risk-low",
  success: "bg-risk-low-bg text-risk-low",
  medium: "bg-risk-medium-bg text-risk-medium",
  warning: "bg-risk-medium-bg text-risk-medium",
  high: "bg-risk-high-bg text-risk-high",
  danger: "bg-risk-high-bg text-risk-high",
  error: "bg-risk-high-bg text-risk-high",
};

const SIZES = {
  sm: "px-2 py-0.5 text-[11px]",
  md: "px-2.5 py-1 text-xs",
};

export function resolveBadgeClasses({ tone, variant, size = "md" } = {}) {
  const key = tone ?? variant ?? "neutral";
  const toneClasses = TONES[key] || TONES.neutral;
  const sizeClasses = SIZES[size] || SIZES.md;
  return `${sizeClasses} ${toneClasses}`;
}

export default function Badge({ children, tone, variant, size = "md", className = "", ...rest }) {
  const variantClasses = resolveBadgeClasses({ tone, variant, size });
  return (
    <span
      className={`inline-flex items-center rounded-full font-medium ${variantClasses} ${className}`}
      {...rest}
    >
      {children}
    </span>
  );
}
