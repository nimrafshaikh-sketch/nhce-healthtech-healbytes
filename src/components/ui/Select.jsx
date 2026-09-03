import React from "react";
import { ChevronDown } from "lucide-react";

export default function Select({ label, error, className = "", children, id, ...props }) {
  const selectId = id || props.name;
  return (
    <label className="block" htmlFor={selectId}>
      {label && <span className="mb-1.5 block text-sm font-medium text-ink-700">{label}</span>}
      <div className="relative">
        <select
          id={selectId}
          className={`w-full appearance-none rounded-xl border bg-white px-3.5 py-2.5 pr-9 text-sm text-ink-900 outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-100 ${
            error ? "border-risk-high" : "border-ink-300/40"
          } ${className}`}
          {...props}
        >
          {children}
        </select>
        <ChevronDown size={16} className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-ink-500" />
      </div>
      {error && <span className="mt-1 block text-xs text-risk-high">{error}</span>}
    </label>
  );
}
