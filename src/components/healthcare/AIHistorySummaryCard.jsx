import React from "react";
import { Activity, Pill, FlaskConical, Calendar, TrendingUp, TrendingDown, Minus, CheckCircle, AlertTriangle, HelpCircle } from "lucide-react";
import Badge from "../ui/Badge";

function TrendIcon({ trend }) {
  if (trend === "improving" || trend === "decreasing") {
    return <TrendingDown size={16} className="text-emerald-600" />;
  }
  if (trend === "worsening" || trend === "increasing") {
    return <TrendingUp size={16} className="text-amber-600" />;
  }
  return <Minus size={16} className="text-ink-400" />;
}

function AdherenceStatusBadge({ status }) {
  if (status === "adherent") {
    return (
      <Badge variant="success" size="sm">
        <CheckCircle size={12} className="mr-1 inline" /> Adherent
      </Badge>
    );
  }
  if (status === "partially_adherent") {
    return (
      <Badge variant="warning" size="sm">
        <AlertTriangle size={12} className="mr-1 inline" /> Partially Adherent
      </Badge>
    );
  }
  if (status === "non_adherent") {
    return (
      <Badge variant="danger" size="sm">
        <AlertTriangle size={12} className="mr-1 inline" /> Non-Adherent
      </Badge>
    );
  }
  return (
    <Badge variant="neutral" size="sm">
      <HelpCircle size={12} className="mr-1 inline" /> Unknown
    </Badge>
  );
}

export default function AIHistorySummaryCard({ summary, loading = false }) {
  if (loading) {
    return (
      <div className="rounded-2xl border border-ink-300/15 bg-white p-6 shadow-card animate-pulse">
        <div className="h-5 w-48 rounded bg-ink-100" />
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <div className="h-24 rounded-xl bg-ink-50" />
          <div className="h-24 rounded-xl bg-ink-50" />
        </div>
      </div>
    );
  }

  if (!summary || !summary.history) {
    return null;
  }

  const { history } = summary;
  const { symptom_trend, vital_trend, medication_adherence, latest_lab, open_follow_up } = history;

  return (
    <div className="rounded-2xl border border-ink-300/15 bg-white p-6 shadow-card">
      <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h3 className="text-base font-semibold text-ink-900 flex items-center gap-2">
            <Activity size={18} className="text-brand-600" />
            AI Clinical History Summary
          </h3>
          <p className="text-xs text-ink-400">
            Computed from {history.checkin_count || 0} check-ins · {history.days_since_last_checkin !== null ? `${history.days_since_last_checkin} days since last check-in` : "No prior check-ins"}
          </p>
        </div>
        {medication_adherence && (
          <div className="mt-2 sm:mt-0">
            <AdherenceStatusBadge status={medication_adherence.overall_status} />
          </div>
        )}
      </div>

      <div className="mt-5 grid gap-4 sm:grid-cols-2">
        {/* Symptom Trend */}
        {symptom_trend && (
          <div className="rounded-xl border border-ink-300/15 bg-ink-50/40 p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-ink-500">Symptom Trend</span>
              <div className="flex items-center gap-1.5 font-medium text-xs text-ink-700 capitalize">
                <TrendIcon trend={symptom_trend.trend} />
                {symptom_trend.trend.replace("_", " ")}
              </div>
            </div>
            <p className="mt-2 text-xs text-ink-600 leading-relaxed">{symptom_trend.detail}</p>
          </div>
        )}

        {/* Medication Adherence */}
        {medication_adherence && (
          <div className="rounded-xl border border-ink-300/15 bg-ink-50/40 p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-ink-500 flex items-center gap-1">
                <Pill size={13} className="text-brand-600" /> Medication Adherence
              </span>
              <span className="text-xs font-medium text-ink-700 capitalize">{medication_adherence.overall_status.replace("_", " ")}</span>
            </div>
            <p className="mt-2 text-xs text-ink-600 leading-relaxed">{medication_adherence.detail}</p>
          </div>
        )}

        {/* Latest Lab Result */}
        {latest_lab && (
          <div className="rounded-xl border border-ink-300/15 bg-ink-50/40 p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-ink-500 flex items-center gap-1">
                <FlaskConical size={13} className="text-brand-600" /> Latest Lab Result
              </span>
              <Badge variant="neutral" size="sm">{latest_lab.test_name}</Badge>
            </div>
            <p className="mt-2 text-sm font-semibold text-ink-800">{latest_lab.result_text || "No result text available"}</p>
            {latest_lab.result_date && (
              <p className="mt-1 text-[11px] text-ink-400">Recorded: {new Date(latest_lab.result_date).toLocaleDateString()}</p>
            )}
          </div>
        )}

        {/* Open Follow-up */}
        {open_follow_up && (
          <div className="rounded-xl border border-ink-300/15 bg-ink-50/40 p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-ink-500 flex items-center gap-1">
                <Calendar size={13} className="text-brand-600" /> Upcoming Follow-up
              </span>
              <Badge variant="info" size="sm">{open_follow_up.status}</Badge>
            </div>
            <p className="mt-2 text-sm font-semibold text-ink-800">{open_follow_up.reason || "Clinical Follow-up"}</p>
            <p className="mt-1 text-[11px] text-ink-400">Scheduled: {new Date(open_follow_up.scheduled_at).toLocaleString()}</p>
          </div>
        )}
      </div>

      {/* Vital Trends if present */}
      {vital_trend && Object.keys(vital_trend).length > 0 && (
        <div className="mt-4 rounded-xl border border-ink-300/15 bg-ink-50/40 p-4">
          <span className="text-xs font-semibold uppercase tracking-wider text-ink-500">Vital Signs Trends</span>
          <div className="mt-2 flex flex-wrap gap-3">
            {Object.entries(vital_trend).map(([vital, info]) => (
              <div key={vital} className="flex items-center gap-2 rounded-lg bg-white px-3 py-1.5 text-xs shadow-sm border border-ink-300/10">
                <span className="capitalize font-medium text-ink-700">{vital.replace("_", " ")}:</span>
                <span className="text-ink-900 font-semibold">{info.latest_value}</span>
                <TrendIcon trend={info.trend} />
                <span className="text-[11px] text-ink-400">({info.delta > 0 ? `+${info.delta}` : info.delta})</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <p className="mt-4 text-[11px] text-ink-400 italic">
        Deterministic calculation over structured clinical records. Follows patient history guidelines.
      </p>
    </div>
  );
}
