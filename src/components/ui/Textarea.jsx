import React from "react";

export default function Textarea({ label, error, hint, className = "", id, rows = 4, ...props }) {
  const inputId = id || props.name;
  return (
    <label className="block" htmlFor={inputId}>
      {label && <span className="mb-1.5 block text-sm font-medium text-ink-700">{label}</span>}
      <textarea
        id={inputId}
        rows={rows}
        className={`w-full resize-none rounded-xl border bg-white px-3.5 py-2.5 text-sm text-ink-900 placeholder:text-ink-300 outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-100 ${
          error ? "border-risk-high" : "border-ink-300/40"
        } ${className}`}
        {...props}
      />
      {hint && !error && <span className="mt-1 block text-xs text-ink-500">{hint}</span>}
      {error && <span className="mt-1 block text-xs text-risk-high">{error}</span>}
    </label>
  );
}
