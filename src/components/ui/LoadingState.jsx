import React from "react";
import { Loader2 } from "lucide-react";

export default function LoadingState({ label = "Loading…" }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 text-ink-500">
      <Loader2 className="animate-spin text-brand-600" size={26} />
      <p className="text-sm">{label}</p>
    </div>
  );
}
