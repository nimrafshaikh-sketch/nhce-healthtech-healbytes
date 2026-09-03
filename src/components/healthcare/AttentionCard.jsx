import React from "react";
import RiskBadge from "./RiskBadge";
import Avatar from "../ui/Avatar";
import Button from "../ui/Button";
import { formatRelativeTime } from "../../utils/dateUtils";

export default function AttentionCard({ patient, onReview }) {
  return (
    <div className="rounded-2xl border border-ink-300/15 bg-white p-5 shadow-card">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <Avatar name={patient.name} initials={patient.avatarInitials} size="lg" />
          <div>
            <RiskBadge level={patient.riskLevel} />
            <p className="mt-1.5 text-base font-semibold text-ink-900">{patient.name}</p>
            <p className="mt-1 max-w-md text-sm text-ink-600">{patient.reason}</p>
          </div>
        </div>
        <div className="shrink-0 text-right">
          <p className="text-2xl font-bold text-ink-900">{patient.riskScore}</p>
          <p className="text-[10px] uppercase tracking-wide text-ink-300">AI Risk Score</p>
        </div>
      </div>
      <div className="mt-4 flex items-center justify-between border-t border-ink-300/10 pt-3">
        <p className="text-xs text-ink-500">
          Last check-in: {patient.lastCheckIn ? formatRelativeTime(patient.lastCheckIn) : "—"}
        </p>
        <Button size="sm" onClick={onReview}>
          Review Patient
        </Button>
      </div>
    </div>
  );
}
