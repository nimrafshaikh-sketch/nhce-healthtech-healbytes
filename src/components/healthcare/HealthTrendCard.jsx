import React from "react";
import { TrendingUp, TrendingDown } from "lucide-react";

export default function HealthTrendCard({ trend = "Improving", direction = "up" }) {
  const Icon = direction === "up" ? TrendingUp : TrendingDown;
  return (
    <div className="rounded-2xl border border-ink-300/15 bg-white p-4 shadow-card">
      <p className="text-xs font-medium uppercase tracking-wide text-ink-300">Health Trend</p>
      <div className="mt-1.5 flex items-center gap-2">
        <Icon size={18} className={direction === "up" ? "text-risk-low" : "text-risk-high"} />
        <span className="text-lg font-semibold text-ink-900">{trend}</span>
      </div>
    </div>
  );
}
