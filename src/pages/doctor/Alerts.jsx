import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ShieldCheck } from "lucide-react";
import Topbar from "../../components/layout/Topbar";
import AlertCard from "../../components/healthcare/AlertCard";
import EmptyState from "../../components/ui/EmptyState";
import { useData } from "../../context/DataContext";

const FILTERS = [
  { key: "ALL", label: "All" },
  { key: "HIGH", label: "High Risk" },
  { key: "MEDIUM", label: "Medium Risk" },
  { key: "RESOLVED", label: "Resolved" },
];

export default function Alerts() {
  const { alerts, resolveAlert } = useData();
  const navigate = useNavigate();
  const [filter, setFilter] = useState("ALL");

  const filtered = alerts
    .filter((a) => {
      if (filter === "ALL") return true;
      if (filter === "RESOLVED") return a.status === "RESOLVED";
      return a.riskLevel === filter && a.status === "ACTIVE";
    })
    .sort((a, b) => new Date(b.detectedAt) - new Date(a.detectedAt));

  return (
    <>
      <Topbar title="Alerts" subtitle="AI-detected health risks requiring attention." />
      <main className="flex-1 px-6 py-6">
        <div className="mb-5 flex flex-wrap gap-2">
          {FILTERS.map((f) => (
            <button
              key={f.key}
              onClick={() => setFilter(f.key)}
              className={`rounded-full px-3.5 py-1.5 text-sm font-medium transition ${
                filter === f.key
                  ? "bg-brand-700 text-white"
                  : "border border-ink-300/25 bg-white text-ink-600 hover:bg-canvas-soft"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>

        {filtered.length ? (
          <div className="grid gap-4 md:grid-cols-2">
            {filtered.map((a) => (
              <AlertCard
                key={a.id}
                alert={a}
                onReview={() => navigate(`/doctor/patients/${a.patientId}`)}
                onResolve={() => resolveAlert(a.id)}
              />
            ))}
          </div>
        ) : (
          <EmptyState icon={ShieldCheck} title="No alerts right now" description="All your patients are currently stable." />
        )}
      </main>
    </>
  );
}
