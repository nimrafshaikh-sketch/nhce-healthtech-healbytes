import React from "react";
import { Check, CheckCircle2, AlertCircle, Clock, Calendar, Edit3 } from "lucide-react";
import { formatTime } from "../../utils/dateUtils";

export default function MedicationCard({ medication, onMarkTaken, onMarkMissed, onEdit, readOnly = false }) {
  const isTaken = medication.status === "TAKEN";
  const isMissed = medication.status === "MISSED";

  const scheduleFormatted = medication.reminder_times && medication.reminder_times.length > 0
    ? medication.reminder_times.map((t) => {
        const [h, m] = t.split(":");
        const hour = parseInt(h, 10);
        const ampm = hour >= 12 ? "PM" : "AM";
        const hour12 = hour % 12 || 12;
        return `${hour12}:${m} ${ampm}`;
      }).join(", ")
    : medication.frequency ? medication.frequency.replace("_", " ").toUpperCase() : "As directed";

  // Calculate course duration and days remaining
  let durationInfo = null;
  const startDateStr = medication.startDate || medication.start_date;
  const endDateStr = medication.endDate || medication.end_date;

  if (endDateStr) {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const end = new Date(endDateStr);
    end.setHours(0, 0, 0, 0);
    const start = startDateStr ? new Date(startDateStr) : today;
    start.setHours(0, 0, 0, 0);

    const totalDays = Math.max(1, Math.round((end - start) / (1000 * 60 * 60 * 24)));
    const remainingDays = Math.round((end - today) / (1000 * 60 * 60 * 24));

    if (remainingDays < 0) {
      durationInfo = {
        isCompleted: true,
        label: `Course completed (${totalDays} days)`,
        tone: "bg-ink-100 text-ink-600 border-ink-200",
      };
    } else if (remainingDays === 0) {
      durationInfo = {
        isCompleted: false,
        label: `Last day of course (${totalDays} days total)`,
        tone: "bg-amber-50 text-amber-800 border-amber-200",
      };
    } else {
      durationInfo = {
        isCompleted: false,
        label: `${totalDays}-day course · ${remainingDays} days remaining`,
        tone: "bg-brand-50 text-brand-700 border-brand-200",
      };
    }
  }

  return (
    <div className={`flex items-center justify-between gap-3 rounded-2xl border p-4 shadow-card transition ${
      isTaken ? "bg-emerald-50/40 border-emerald-200" : isMissed ? "bg-amber-50/40 border-amber-200" : "bg-white border-ink-300/15"
    }`}>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 flex-wrap">
          <p className="text-sm font-bold text-ink-900">{medication.name}</p>
          <span className="text-[11px] font-semibold text-brand-800 bg-brand-50 border border-brand-200 px-2 py-0.5 rounded-full">
            {medication.dosage}
          </span>
          {durationInfo && (
            <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${durationInfo.tone}`}>
              📅 {durationInfo.label}
            </span>
          )}
        </div>
        <p className="text-xs text-ink-500 mt-1">
          {medication.instructions || "Take as prescribed"}
        </p>
        <div className="mt-2 flex items-center gap-2 flex-wrap">
          <span className="text-[11px] font-medium text-ink-700 bg-canvas-soft border border-ink-200 px-2 py-0.5 rounded-md inline-flex items-center gap-1">
            <Clock size={11} className="text-brand-600" /> ⏰ {scheduleFormatted}
          </span>
          {endDateStr && (
            <span className="text-[11px] text-ink-500 inline-flex items-center gap-1">
              <Calendar size={11} className="text-ink-400" /> Until {new Date(endDateStr).toLocaleDateString()}
            </span>
          )}
          {medication.prescribed_by_name && (
            <span className="text-[10px] text-ink-400">
              Dr. {medication.prescribed_by_name}
            </span>
          )}
        </div>
        {isTaken && (
          <p className="mt-2 flex items-center gap-1.5 text-xs font-semibold text-emerald-700 bg-emerald-100/70 px-2.5 py-1 rounded-lg w-fit">
            <CheckCircle2 size={13} className="text-emerald-600" /> Taken at {medication.takenAt ? formatTime(medication.takenAt) : "Scheduled Time"}
          </p>
        )}
        {isMissed && (
          <p className="mt-2 flex items-center gap-1.5 text-xs font-semibold text-amber-700 bg-amber-100/70 px-2.5 py-1 rounded-lg w-fit">
            <AlertCircle size={13} className="text-amber-600" /> Marked Missed
          </p>
        )}
      </div>

      {/* Doctor view: Read-only adherence status + optional Edit button */}
      {readOnly ? (
        <div className="shrink-0 flex items-center gap-2">
          {onEdit && (
            <button
              type="button"
              onClick={() => onEdit(medication)}
              className="flex items-center gap-1 text-xs font-medium text-ink-600 bg-canvas-soft hover:bg-ink-100 border border-ink-200 px-2.5 py-1.5 rounded-xl transition"
            >
              <Edit3 size={13} /> Edit
            </button>
          )}
          <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold ${
            isTaken
              ? "bg-emerald-100 text-emerald-800 border border-emerald-200"
              : isMissed
              ? "bg-amber-100 text-amber-800 border border-amber-200"
              : "bg-brand-50 text-brand-700 border border-brand-200"
          }`}>
            {isTaken ? "Dose Taken" : isMissed ? "Dose Missed" : "Active"}
          </span>
        </div>
      ) : (
        /* Patient view: Action buttons */
        !isTaken && !isMissed && (
          <div className="flex shrink-0 items-center gap-2">
            <button
              type="button"
              onClick={onMarkMissed}
              className="rounded-xl border border-ink-200 bg-canvas-soft px-3 py-1.5 text-xs font-medium text-ink-600 hover:bg-ink-100 transition"
            >
              Missed
            </button>
            <button
              type="button"
              onClick={onMarkTaken}
              className="flex items-center gap-1.5 rounded-xl bg-brand-700 px-3.5 py-1.5 text-xs font-semibold text-white shadow-sm hover:bg-brand-800 active:scale-95 transition"
            >
              <Check size={13} strokeWidth={2.5} /> Taken
            </button>
          </div>
        )
      )}
    </div>
  );
}
