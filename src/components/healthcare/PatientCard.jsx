import React from "react";
import { ChevronRight } from "lucide-react";
import RiskBadge from "./RiskBadge";
import Avatar from "../ui/Avatar";
import { formatRelativeTime } from "../../utils/dateUtils";

export default function PatientCard({ patient, onClick }) {
  return (
    <button
      onClick={onClick}
      className="flex w-full items-center gap-3 rounded-2xl border border-ink-300/15 bg-white p-4 text-left shadow-card transition hover:border-brand-200 hover:shadow-raised"
    >
      <Avatar name={patient.name} initials={patient.avatarInitials} />
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <p className="truncate text-sm font-semibold text-ink-900">{patient.name}</p>
          <RiskBadge level={patient.riskLevel} size="sm" />
        </div>
        <p className="mt-0.5 truncate text-xs text-ink-500">{patient.condition}</p>
        <p className="mt-1 text-xs text-ink-300">
          {patient.lastCheckIn ? `Checked in ${formatRelativeTime(patient.lastCheckIn)}` : "No check-ins yet"}
        </p>
      </div>
      <ChevronRight size={18} className="shrink-0 text-ink-300" />
    </button>
  );
}
