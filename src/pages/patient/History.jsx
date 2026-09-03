import React from "react";
import RiskBadge from "../../components/healthcare/RiskBadge";
import EmptyState from "../../components/ui/EmptyState";
import { useAuth } from "../../context/AuthContext";
import { useData } from "../../context/DataContext";
import { formatDayLabel, formatTime } from "../../utils/dateUtils";

export default function PatientHistory() {
  const { user } = useAuth();
  const { getCheckinsForPatient } = useData();
  const checkins = getCheckinsForPatient(user.id);

  return (
    <div className="flex-1 px-5 pb-6 pt-8">
      <h1 className="text-lg font-semibold text-ink-900">History</h1>
      <p className="mt-1 text-sm text-ink-500">Your care journey over time.</p>

      <div className="mt-6">
        {checkins.length ? (
          checkins.map((c, i) => (
            <div key={c.id} className="flex gap-3">
              <div className="flex flex-col items-center">
                <span className="mt-1.5 h-2 w-2 rounded-full bg-brand-500" />
                {i !== checkins.length - 1 && <span className="mt-1 w-px flex-1 bg-ink-300/20" />}
              </div>
              <div className="pb-5">
                <p className="text-xs text-ink-300">
                  {formatDayLabel(c.date)} · {formatTime(c.date)}
                </p>
                <p className="text-sm font-medium text-ink-900">Daily Check-in</p>
                <p className="mt-0.5 text-xs text-ink-500">Symptoms monitored</p>
                <div className="mt-1.5">
                  <RiskBadge level={c.riskLevel} size="sm" />
                </div>
              </div>
            </div>
          ))
        ) : (
          <EmptyState title="No history yet" description="Your care activity will appear here." />
        )}
      </div>
    </div>
  );
}
