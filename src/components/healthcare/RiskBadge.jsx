import React from "react";
import { AlertTriangle, CheckCircle2, AlertCircle } from "lucide-react";

const CONFIG = {
  LOW: { label: "Low Risk", tone: "bg-risk-low-bg text-risk-low", icon: CheckCircle2 },
  MEDIUM: { label: "Medium Risk", tone: "bg-risk-medium-bg text-risk-medium", icon: AlertCircle },
  HIGH: { label: "High Risk", tone: "bg-risk-high-bg text-risk-high", icon: AlertTriangle },
};

export default function RiskBadge({ level = "LOW", size = "md" }) {
  const cfg = CONFIG[level] || CONFIG.LOW;
  const Icon = cfg.icon;
  const sizeCls = size === "sm" ? "text-[11px] px-2 py-0.5 gap-1" : "text-xs px-2.5 py-1 gap-1.5";
  return (
    <span className={`inline-flex items-center rounded-full font-semibold uppercase tracking-wide ${cfg.tone} ${sizeCls}`}>
      <Icon size={size === "sm" ? 12 : 13} />
      {cfg.label}
    </span>
  );
}
