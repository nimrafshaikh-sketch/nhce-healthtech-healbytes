import React from "react";
import { useNavigate } from "react-router-dom";
import { CalendarCheck, ClipboardList, Percent, Users } from "lucide-react";
import Topbar from "../../components/layout/Topbar";
import AttentionCard from "../../components/healthcare/AttentionCard";
import InsightItem from "../../components/healthcare/InsightItem";
import EmptyState from "../../components/ui/EmptyState";
import { useAuth } from "../../context/AuthContext";
import { useData } from "../../context/DataContext";
import { formatDayLabel, formatTime } from "../../utils/dateUtils";

function greeting() {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

export default function DoctorDashboard() {
  const { user } = useAuth();
  const { patients, alerts } = useData();
  const navigate = useNavigate();

  const needingAttention = [...patients]
    .filter((p) => p.riskLevel !== "LOW")
    .sort((a, b) => b.riskScore - a.riskScore)
    .slice(0, 4);

  const checkedInToday = patients.filter(
    (p) => p.lastCheckIn && Date.now() - new Date(p.lastCheckIn).getTime() < 24 * 60 * 60 * 1000
  ).length;
  const pendingCheckins = Math.max(patients.length - checkedInToday, 0);
  const followUpsToday = patients.filter(
    (p) => p.nextFollowUp && formatDayLabel(p.nextFollowUp.date) === "Today"
  ).length;
  const avgAdherence = patients.length
    ? Math.round(patients.reduce((sum, p) => sum + (p.medicationAdherencePct || 0), 0) / patients.length)
    : 0;

  const recentInsights = [...alerts].sort((a, b) => new Date(b.detectedAt) - new Date(a.detectedAt)).slice(0, 4);

  const upcoming = [...patients]
    .filter((p) => p.nextFollowUp)
    .sort((a, b) => new Date(a.nextFollowUp.date) - new Date(b.nextFollowUp.date))
    .slice(0, 4);

  const stats = [
    { label: "Follow-ups Today", value: followUpsToday, icon: CalendarCheck },
    { label: "Checked In Today", value: checkedInToday, icon: Users },
    { label: "Pending Check-ins", value: pendingCheckins, icon: ClipboardList },
    { label: "Avg. Adherence", value: `${avgAdherence}%`, icon: Percent },
  ];

  return (
    <>
      <Topbar
        title={`${greeting()}, ${user?.name?.split(" ")[0] || "Doctor"}`}
        subtitle="Here's what's happening with your patients today."
      />
      <main className="flex-1 space-y-8 px-6 py-6">
        <section>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-base font-semibold text-ink-900">Patients Needing Attention</h2>
            <button
              onClick={() => navigate("/doctor/patients")}
              className="text-sm font-medium text-brand-700 hover:underline"
            >
              View all
            </button>
          </div>
          {needingAttention.length ? (
            <div className="grid gap-4 md:grid-cols-2">
              {needingAttention.map((p) => (
                <AttentionCard key={p.id} patient={p} onReview={() => navigate(`/doctor/patients/${p.id}`)} />
              ))}
            </div>
          ) : (
            <EmptyState title="All patients are stable" description="No one needs urgent attention right now." />
          )}
        </section>

        <section>
          <h2 className="mb-3 text-base font-semibold text-ink-900">Today's Care</h2>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {stats.map(({ label, value, icon: Icon }) => (
              <div key={label} className="rounded-2xl border border-ink-300/15 bg-white p-4 shadow-card">
                <Icon size={16} className="text-brand-600" />
                <p className="mt-2 text-xl font-bold text-ink-900">{value}</p>
                <p className="text-xs text-ink-500">{label}</p>
              </div>
            ))}
          </div>
        </section>

        <div className="grid gap-8 lg:grid-cols-2">
          <section>
            <h2 className="mb-3 text-base font-semibold text-ink-900">Recent AI Insights</h2>
            {recentInsights.length ? (
              <div className="rounded-2xl border border-ink-300/15 bg-white p-5 shadow-card">
                {recentInsights.map((a, i) => (
                  <InsightItem
                    key={a.id}
                    alert={a}
                    isLast={i === recentInsights.length - 1}
                    onReview={() => navigate(`/doctor/patients/${a.patientId}`)}
                  />
                ))}
              </div>
            ) : (
              <EmptyState title="No AI insights yet" description="Insights appear as patients complete check-ins." />
            )}
          </section>

          <section>
            <h2 className="mb-3 text-base font-semibold text-ink-900">Upcoming Follow-ups</h2>
            {upcoming.length ? (
              <div className="space-y-3">
                {upcoming.map((p) => (
                  <div
                    key={p.id}
                    className="flex items-center justify-between rounded-2xl border border-ink-300/15 bg-white p-4 shadow-card"
                  >
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-ink-900">{p.name}</p>
                      <p className="truncate text-xs text-ink-500">{p.nextFollowUp.reason}</p>
                    </div>
                    <div className="shrink-0 text-right">
                      <p className="text-xs font-medium text-ink-700">{formatDayLabel(p.nextFollowUp.date)}</p>
                      <p className="text-xs text-ink-300">{formatTime(p.nextFollowUp.date)}</p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState title="No upcoming follow-ups" description="Scheduled follow-ups will appear here." />
            )}
          </section>
        </div>
      </main>
    </>
  );
}
