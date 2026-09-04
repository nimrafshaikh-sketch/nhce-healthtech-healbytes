import React from "react";
import {
  Activity,
  Pill,
  FlaskConical,
  Calendar,
  TrendingUp,
  TrendingDown,
  Minus,
  CheckCircle,
  AlertTriangle,
  HelpCircle,
  FileText,
  ExternalLink,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import Badge from "../ui/Badge";
import Button from "../ui/Button";
import { getDocumentViewUrl } from "../../api/documents.api";

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

  if (!summary) {
    return null;
  }

  const { history, clinical_brief } = summary;
  const symptom_trend = history?.symptom_trend;
  const vital_trend = history?.vital_trend;
  const medication_adherence = history?.medication_adherence;
  const latest_lab = history?.latest_lab;
  const open_follow_up = history?.open_follow_up;

  return (
    <div className="rounded-2xl border border-ink-300/15 bg-white p-6 shadow-card space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between border-b border-ink-100 pb-4">
        <div>
          <h3 className="text-base font-semibold text-ink-900 flex items-center gap-2">
            <Activity size={18} className="text-brand-600" />
            Longitudinal Clinical Brief & History
          </h3>
          <p className="text-xs text-ink-400">
            Authoritative records & patient-scoped document intelligence · {history?.checkin_count || 0} check-ins
          </p>
        </div>
        {medication_adherence && (
          <div className="mt-2 sm:mt-0">
            <AdherenceStatusBadge status={medication_adherence.overall_status} />
          </div>
        )}
      </div>

      {/* Clinical Narrative / Synthesis */}
      {clinical_brief && (
        <div className="rounded-xl border border-brand-200/50 bg-brand-50/30 p-4">
          <div className="flex items-center gap-2 mb-2">
            <Sparkles size={16} className="text-brand-600" />
            <span className="text-xs font-bold uppercase tracking-wider text-brand-900">
              AI Longitudinal Synthesis
            </span>
            <span className="text-[10px] bg-brand-100 text-brand-700 px-2 py-0.5 rounded-full font-medium">
              Patient-Scoped RAG Grounded
            </span>
          </div>
          <p className="text-sm text-ink-800 leading-relaxed font-normal">
            {clinical_brief.narrative}
          </p>
        </div>
      )}

      {/* Longitudinal Biomarker Trends (Temporal Reasoning) */}
      {clinical_brief?.longitudinal_trends?.length > 0 && (
        <div className="space-y-3">
          <h4 className="text-xs font-bold uppercase tracking-wider text-ink-500 flex items-center gap-1.5">
            <TrendingUp size={14} className="text-brand-600" />
            Biomarker Trajectory & Longitudinal Trends
          </h4>
          <div className="grid gap-3 sm:grid-cols-2">
            {clinical_brief.longitudinal_trends.map((trend, idx) => (
              <div key={idx} className="rounded-xl border border-ink-200 bg-canvas-soft/40 p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-semibold text-ink-900">{trend.biomarker}</span>
                  <div className="flex items-center gap-1 text-xs font-medium capitalize text-ink-700">
                    <TrendIcon trend={trend.trend} />
                    {trend.trend}
                  </div>
                </div>

                {/* AI Observation vs Source Facts distinction */}
                <div className="rounded-lg bg-amber-50/60 border border-amber-200/60 p-2.5 text-xs text-amber-900">
                  <span className="font-semibold text-amber-800">AI Observation: </span>
                  {trend.summary}
                </div>

                <div className="text-xs text-ink-600 space-y-1">
                  <p className="font-medium text-ink-500 text-[11px] uppercase tracking-wider">Source Chronology:</p>
                  {trend.points?.map((pt, pIdx) => (
                    <div key={pIdx} className="flex justify-between items-center text-[12px] bg-white px-2 py-1 rounded border border-ink-100">
                      <span className="text-ink-500">{pt.date || `Record #${pIdx + 1}`}:</span>
                      <span className="font-bold text-ink-900">{pt.value} {pt.unit || "%"}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Grid of Key Metrics */}
      <div className="grid gap-4 sm:grid-cols-2">
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

      {/* Active Medications with Doctor Provenance */}
      {clinical_brief?.active_medications?.length > 0 && (
        <div className="rounded-xl border border-ink-200 bg-canvas-soft/30 p-4">
          <span className="text-xs font-bold uppercase tracking-wider text-ink-500 flex items-center gap-1.5 mb-3">
            <Pill size={14} className="text-brand-600" />
            Active Clinical Prescriptions (With Prescribing Doctor Provenance)
          </span>
          <div className="grid gap-2 sm:grid-cols-2">
            {clinical_brief.active_medications.map((med, idx) => (
              <div key={idx} className="flex items-center justify-between rounded-lg bg-white p-2.5 border border-ink-100 text-xs shadow-sm">
                <div>
                  <p className="font-bold text-ink-900">{med.name} {med.dosage}</p>
                  <p className="text-[11px] text-ink-500">{med.frequency} · {med.instructions || "Standard dose"}</p>
                </div>
                {med.prescribed_by && (
                  <span className="text-[11px] bg-brand-50 text-brand-800 border border-brand-200 px-2 py-0.5 rounded-full font-medium">
                    {med.prescribed_by}
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Source Documents with Clickable Original Report Links */}
      {clinical_brief?.source_documents?.length > 0 && (
        <div className="rounded-xl border border-emerald-200/70 bg-emerald-50/30 p-4">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-bold uppercase tracking-wider text-emerald-900 flex items-center gap-1.5">
              <ShieldCheck size={14} className="text-emerald-700" />
              Source Documents & Provenance (Authoritative Grounding)
            </span>
            <span className="text-[11px] text-emerald-700 font-medium">
              {clinical_brief.source_documents.length} verified report(s)
            </span>
          </div>

          <div className="space-y-2">
            {clinical_brief.source_documents.map((doc) => (
              <div
                key={doc.id}
                className="flex items-center justify-between rounded-xl bg-white p-3 border border-emerald-100 shadow-sm"
              >
                <div className="flex items-center gap-3">
                  <FileText size={18} className="text-emerald-600 shrink-0" />
                  <div>
                    <p className="text-xs font-bold text-ink-900">{doc.title}</p>
                    <p className="text-[11px] text-ink-400">
                      {doc.type} · {doc.date ? new Date(doc.date).toLocaleDateString() : "Recent"}
                    </p>
                  </div>
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  className="text-xs text-brand-700 border-brand-300 hover:bg-brand-50"
                  onClick={() => {
                    const url = getDocumentViewUrl(doc.id);
                    window.open(url, "_blank");
                  }}
                >
                  <ExternalLink size={12} className="mr-1 inline" />
                  View Original Report
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Vital Trends if present */}
      {vital_trend && Object.keys(vital_trend).length > 0 && (
        <div className="rounded-xl border border-ink-300/15 bg-ink-50/40 p-4">
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

      <p className="text-[11px] text-ink-400 italic">
        Deterministic synthesis of structured PostgreSQL records & patient-scoped clinical document RAG retrieval.
      </p>
    </div>
  );
}

