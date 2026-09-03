import React from "react";
import { ShieldCheck } from "lucide-react";
import RiskBadge from "../../components/healthcare/RiskBadge";
import EmptyState from "../../components/ui/EmptyState";
import { useAuth } from "../../context/AuthContext";
import { useData } from "../../context/DataContext";
import { formatRelativeTime } from "../../utils/dateUtils";

export default function PatientAlerts() {
  const { user } = useAuth();
  const { getAlertsForPatient } = useData();
  const alerts = [...getAlertsForPatient(user.id)].sort((a, b) => new Date(b.detectedAt) - new Date(a.detectedAt));

  return (
    <div className="flex-1 px-5 pb-6 pt-8">
      <h1 className="text-lg font-semibold text-ink-900">Alerts</h1>
      <p className="mt-1 text-sm text-ink-500">Updates your care team has been notified about.</p>

      <div className="mt-6 space-y-3">
        {alerts.length ? (
          alerts.map((a) => (
            <div key={a.id} className="rounded-2xl border border-ink-300/15 bg-white p-4 shadow-card">
              <div className="flex items-center justify-between">
                <RiskBadge level={a.riskLevel} size="sm" />
                <span className="text-xs text-ink-300">{formatRelativeTime(a.detectedAt)}</span>
              </div>
              <p className="mt-2 text-sm text-ink-800">{a.message}</p>
              {a.status === "RESOLVED" && <p className="mt-1 text-xs font-medium text-ink-300">Resolved</p>}
            </div>
          ))
        ) : (
          <EmptyState icon={ShieldCheck} title="No alerts right now" description="Everything looks stable." />
        )}
      </div>
    </div>
  );
}
