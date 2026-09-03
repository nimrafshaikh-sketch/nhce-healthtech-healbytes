import React, { useEffect, useState } from "react";
import Topbar from "../../components/layout/Topbar";
import LoadingState from "../../components/ui/LoadingState";
import { useData } from "../../context/DataContext";
import { getDoctorAnalytics } from "../../api/analytics.api";

export default function Analytics() {
  const { patients } = useData();
  const [stats, setStats] = useState(null);

  useEffect(() => {
    let active = true;
    getDoctorAnalytics(patients).then((result) => {
      if (active) setStats(result);
    });
    return () => {
      active = false;
    };
  }, [patients]);

  if (!stats) {
    return (
      <>
        <Topbar title="Analytics" subtitle="Practice-wide patient trends." />
        <main className="flex-1 px-6 py-6">
          <LoadingState label="Crunching numbers…" />
        </main>
      </>
    );
  }

  const rows = [
    { label: "Stable", value: stats.low, tone: "bg-risk-low" },
    { label: "Medium Risk", value: stats.medium, tone: "bg-risk-medium" },
    { label: "High Risk", value: stats.high, tone: "bg-risk-high" },
  ];

  return (
    <>
      <Topbar title="Analytics" subtitle="Practice-wide patient trends." />
      <main className="flex-1 space-y-6 px-6 py-6">
        <section className="rounded-2xl border border-ink-300/15 bg-white p-6 shadow-card">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-ink-500">Patient Risk Distribution</h2>
          <div className="mt-4 space-y-3">
            {rows.map((r) => (
              <div key={r.label}>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-ink-700">{r.label}</span>
                  <span className="font-medium text-ink-900">{r.value}</span>
                </div>
                <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-ink-900/5">
                  <div
                    className={`h-full rounded-full ${r.tone}`}
                    style={{ width: `${stats.total ? (r.value / stats.total) * 100 : 0}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </section>

        <div className="grid gap-4 sm:grid-cols-3">
          <div className="rounded-2xl border border-ink-300/15 bg-white p-5 shadow-card">
            <p className="text-xs uppercase tracking-wide text-ink-300">Total Patients</p>
            <p className="mt-1 text-2xl font-bold text-ink-900">{stats.total}</p>
          </div>
          <div className="rounded-2xl border border-ink-300/15 bg-white p-5 shadow-card">
            <p className="text-xs uppercase tracking-wide text-ink-300">Avg. Medication Adherence</p>
            <p className="mt-1 text-2xl font-bold text-ink-900">{stats.avgAdherence}%</p>
          </div>
          <div className="rounded-2xl border border-ink-300/15 bg-white p-5 shadow-card">
            <p className="text-xs uppercase tracking-wide text-ink-300">Needing Follow-up</p>
            <p className="mt-1 text-2xl font-bold text-ink-900">{stats.medium + stats.high}</p>
          </div>
        </div>
      </main>
    </>
  );
}
