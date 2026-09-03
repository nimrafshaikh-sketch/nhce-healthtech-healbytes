import React from "react";
import RiskBadge from "./RiskBadge";
import Avatar from "../ui/Avatar";
import Button from "../ui/Button";
import { formatRelativeTime } from "../../utils/dateUtils";

export default function AlertCard({ alert, onReview, onResolve }) {
  const resolved = alert.status === "RESOLVED";
  return (
    <div className={`rounded-2xl border p-5 shadow-card ${resolved ? "border-ink-300/10 bg-canvas-soft/60" : "border-ink-300/15 bg-white"}`}>
      <div className="flex items-start gap-3">
        <Avatar name={alert.patientName} initials={alert.avatarInitials} />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <RiskBadge level={alert.riskLevel} size="sm" />
            {resolved && <span className="text-xs font-medium text-ink-300">Resolved</span>}
          </div>
          <p className="mt-1.5 text-sm font-semibold text-ink-900">{alert.patientName}</p>
          <p className="mt-0.5 text-sm text-ink-600">{alert.message}</p>
          <p className="mt-2 text-xs text-ink-300">
            AI Score {alert.riskScore} · Detected {formatRelativeTime(alert.detectedAt)}
          </p>
        </div>
      </div>
      <div className="mt-4 flex items-center gap-2 border-t border-ink-300/10 pt-3">
        <Button size="sm" variant="secondary" onClick={onReview}>
          Review Patient
        </Button>
        {!resolved && (
          <Button size="sm" variant="ghost" onClick={onResolve}>
            Mark Resolved
          </Button>
        )}
      </div>
    </div>
  );
}
