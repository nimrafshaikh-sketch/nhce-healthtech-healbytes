import React from "react";
import { Loader2 } from "lucide-react";

const VARIANTS = {
  primary: "bg-brand-700 text-white hover:bg-brand-800 active:bg-brand-900 disabled:bg-brand-200",
  secondary: "bg-white text-ink-900 border border-ink-300/50 hover:bg-canvas-soft disabled:text-ink-300",
  ghost: "bg-transparent text-brand-700 hover:bg-brand-50 disabled:text-ink-300",
  danger: "bg-risk-high text-white hover:opacity-90 disabled:opacity-50",
};

const SIZES = {
  sm: "text-xs px-3 py-1.5 rounded-lg gap-1.5",
  md: "text-sm px-4 py-2.5 rounded-xl gap-2",
  lg: "text-base px-5 py-3 rounded-xl gap-2",
};

export default function Button({
  variant = "primary",
  size = "md",
  fullWidth = false,
  loading = false,
  leftIcon,
  rightIcon,
  className = "",
  children,
  disabled,
  type = "button",
  ...props
}) {
  return (
    <button
      type={type}
      className={`inline-flex items-center justify-center font-medium transition-colors duration-150 disabled:cursor-not-allowed ${VARIANTS[variant]} ${SIZES[size]} ${fullWidth ? "w-full" : ""} ${className}`}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? <Loader2 className="animate-spin" size={16} /> : leftIcon}
      {children}
      {!loading && rightIcon}
    </button>
  );
}
