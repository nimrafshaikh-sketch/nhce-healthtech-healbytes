import React from "react";
import { Check } from "lucide-react";
import { formatTime } from "../../utils/dateUtils";

export default function MedicationCard({ medication, onMarkTaken, onMarkMissed }) {
  const isTaken = medication.status === "TAKEN";
  const isMissed = medication.status === "MISSED";

  return (
    <div className="flex items-center justify-between gap-3 rounded-2xl border border-ink-300/15 bg-white p-4 shadow-card">
      <div className="min-w-0">
        <p className="text-sm font-semibold text-ink-900">{medication.name}</p>
        <p className="text-xs text-ink-500">
          {medication.dosage} · {medication.instructions}
        </p>
        {isTaken && medication.takenAt && (
          <p className="mt-1 flex items-center gap-1 text-xs font-medium text-risk-low">
            <Check size={12} /> Taken at {formatTime(medication.takenAt)}
          </p>
        )}
        {isMissed && <p className="mt-1 text-xs font-medium text-risk-high">Marked missed</p>}
      </div>
      {!isTaken && !isMissed && (
        <div className="flex shrink-0 items-center gap-2">
          <button onClick={onMarkMissed} className="rounded-lg px-3 py-1.5 text-xs font-medium text-ink-500 hover:bg-canvas-soft">
            Missed
          </button>
          <button
            onClick={onMarkTaken}
            className="flex items-center gap-1 rounded-lg bg-brand-700 px-3 py-1.5 text-xs font-medium text-white hover:bg-brand-800"
          >
            <Check size={13} /> Taken
          </button>
        </div>
      )}
    </div>
  );
}
