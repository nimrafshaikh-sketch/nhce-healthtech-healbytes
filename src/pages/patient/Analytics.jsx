import React from "react";
import HealthTrendCard from "../../components/healthcare/HealthTrendCard";
import { useAuth } from "../../context/AuthContext";
import { useData } from "../../context/DataContext";

export default function PatientAnalytics() {
  const { user } = useAuth();
  const { getPatientById, getCheckinsForPatient, getMedicationsForPatient } = useData();
  const patient = getPatientById(user.id) || user;
  const checkins = getCheckinsForPatient(user.id);
  const medications = getMedicationsForPatient(user.id);

  const consistency = Math.min(checkins.length, 7);
  const direction = patient.riskLevel === "LOW" ? "up" : "down";
  const trendLabel =
    patient.riskLevel === "LOW" ? "Improving" : patient.riskLevel === "MEDIUM" ? "Needs monitoring" : "Needs attention";

  return (
    <div className="flex-1 px-5 pb-6 pt-8">
      <h1 className="text-lg font-semibold text-ink-900">Insights</h1>
      <p className="mt-1 text-sm text-ink-500">A simple look at how you're doing.</p>

      <div className="mt-6 space-y-3">
        <HealthTrendCard trend={trendLabel} direction={direction} />

        <div className="rounded-2xl border border-ink-300/15 bg-white p-4 shadow-card">
          <p className="text-xs font-medium uppercase tracking-wide text-ink-300">Check-in Consistency</p>
          <p className="mt-1.5 text-lg font-semibold text-ink-900">{consistency} of 7 days</p>
        </div>

        <div className="rounded-2xl border border-ink-300/15 bg-white p-4 shadow-card">
          <p className="text-xs font-medium uppercase tracking-wide text-ink-300">Medication Adherence</p>
          <p className="mt-1.5 text-lg font-semibold text-ink-900">{patient.medicationAdherencePct}%</p>
        </div>

        <div className="rounded-2xl border border-ink-300/15 bg-white p-4 shadow-card">
          <p className="mb-2 text-xs font-medium uppercase tracking-wide text-ink-300">Risk History</p>
          <div className="flex items-center gap-2">
            {checkins.length ? (
              [...checkins]
                .slice(0, 6)
                .reverse()
                .map((c) => (
                  <span
                    key={c.id}
                    title={c.riskLevel}
                    className={`h-3 w-3 rounded-full ${
                      c.riskLevel === "HIGH" ? "bg-risk-high" : c.riskLevel === "MEDIUM" ? "bg-risk-medium" : "bg-risk-low"
                    }`}
                  />
                ))
            ) : (
              <span className="text-sm text-ink-400">No check-ins yet</span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
