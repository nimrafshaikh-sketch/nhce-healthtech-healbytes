import React from "react";
import RiskBadge from "./RiskBadge";
import { formatTime } from "../../utils/dateUtils";

export default function InsightItem({ alert, onReview, isLast }) {
  return (
    <div className="flex gap-3">
      <div className="flex flex-col items-center">
        <span className="mt-1 h-2 w-2 rounded-full bg-brand-500" />
        {!isLast && <span className="mt-1 w-px flex-1 bg-ink-300/20" />}
      </div>
      <div className="flex-1 pb-5">
        <p className="text-xs text-ink-300">{formatTime(alert.detectedAt)}</p>
        <p className="mt-1 text-sm text-ink-800">{alert.message}</p>
        <div className="mt-1.5 flex flex-wrap items-center gap-2">
          <span className="text-sm font-medium text-ink-900">{alert.patientName}</span>
          <RiskBadge level={alert.riskLevel} size="sm" />
          <button onClick={onReview} className="text-xs font-medium text-brand-700 hover:underline">
            Review
          </button>
        </div>
      </div>
    </div>
  );
}
