import React from "react";
import { FEELING_OPTIONS } from "../../utils/constants";
import RiskBadge from "./RiskBadge";
import { formatDayLabel, formatTime } from "../../utils/dateUtils";

export default function CheckinSummary({ checkin }) {
  const feeling = FEELING_OPTIONS.find((f) => f.value === checkin.overallFeeling);
  const timePart = formatTime(checkin.date);
  return (
    <div className="rounded-2xl border border-ink-300/15 bg-white p-4 shadow-card">
      <div className="flex items-center justify-between">
        <p className="text-xs text-ink-300">
          {formatDayLabel(checkin.date)}{timePart ? ` · ${timePart}` : ""}
        </p>
        <RiskBadge level={checkin.riskLevel} size="sm" />
      </div>
      <p className="mt-2 text-sm text-ink-800">
        {feeling ? `${feeling.emoji} ${feeling.label}` : "Check-in"}
        {checkin.symptoms?.length
          ? ` · ${checkin.symptoms.map((s) => (typeof s === "string" ? s : s.name)).join(", ")}`
          : " · No symptoms reported"}
      </p>
      {checkin.reason && <p className="mt-1 text-xs text-ink-500">{checkin.reason}</p>}
    </div>
  );
}
