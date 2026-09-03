import React, { useEffect } from "react";
import { X } from "lucide-react";

export default function Modal({ open, onClose, title, children, footer, size = "md" }) {
  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e) => e.key === "Escape" && onClose?.();
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  const widths = { sm: "max-w-sm", md: "max-w-md", lg: "max-w-lg" };

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-ink-900/40 p-0 sm:items-center sm:p-4"
      role="dialog"
      aria-modal="true"
    >
      <div className={`max-h-[90vh] w-full overflow-y-auto rounded-t-2xl bg-white shadow-raised sm:rounded-2xl ${widths[size]}`}>
        <div className="flex items-center justify-between border-b border-ink-300/15 px-5 py-4">
          <h2 className="text-base font-semibold text-ink-900">{title}</h2>
          <button onClick={onClose} aria-label="Close" className="rounded-full p-1.5 text-ink-500 hover:bg-canvas-soft">
            <X size={18} />
          </button>
        </div>
        <div className="px-5 py-4">{children}</div>
        {footer && <div className="flex items-center justify-end gap-2 border-t border-ink-300/15 px-5 py-4">{footer}</div>}
      </div>
    </div>
  );
}
