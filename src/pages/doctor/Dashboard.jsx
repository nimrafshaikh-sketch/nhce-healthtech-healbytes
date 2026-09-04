import React from "react";
import { useNavigate } from "react-router-dom";
import { CalendarCheck, ClipboardList, Percent, Users, User, ArrowRight, Clock, Calendar, Sparkles } from "lucide-react";
import Topbar from "../../components/layout/Topbar";
import AttentionCard from "../../components/healthcare/AttentionCard";
import InsightItem from "../../components/healthcare/InsightItem";
import RiskBadge from "../../components/healthcare/RiskBadge";
import EmptyState from "../../components/ui/EmptyState";
import { useAuth } from "../../context/AuthContext";
import { useData } from "../../context/DataContext";
import { formatDayLabel, formatTime, formatRelativeTime } from "../../utils/dateUtils";
import DoctorAgentChat from "../../components/doctor/DoctorAgentChat";

function greeting() {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

export default function DoctorDashboard() {
  const { user } = useAuth();
  const { patients = [], alerts = [], appointments = [] } = useData();
  const navigate = useNavigate();

  const needingAttention = [...patients]
    .filter((p) => p.riskLevel && p.riskLevel !== "LOW")
    .sort((a, b) => (b.riskScore || 0) - (a.riskScore || 0))
    .slice(0, 4);

  const checkedInToday = patients.filter(
    (p) => p.lastCheckIn && Date.now() - new Date(p.lastCheckIn).getTime() < 24 * 60 * 60 * 1000
  ).length;
  const pendingCheckins = Math.max(patients.length - checkedInToday, 0);

  // Real appointment list
  const activeAppointments = [...appointments]
    .filter((a) => a.scheduledAt)
    .sort((a, b) => new Date(a.scheduledAt) - new Date(b.scheduledAt));

  const followUpsToday = activeAppointments.filter(
    (a) => a.scheduledAt && formatDayLabel(a.scheduledAt) === "Today"
  ).length || patients.filter(
    (p) => p.nextFollowUp && formatDayLabel(p.nextFollowUp.date) === "Today"
  ).length;

  const validAdherenceList = patients.filter((p) => p.medicationAdherencePct != null);
  const avgAdherence = validAdherenceList.length
    ? Math.round(validAdherenceList.reduce((sum, p) => sum + (p.medicationAdherencePct || 0), 0) / validAdherenceList.length)
    : 100;

  const recentInsights = [...alerts].sort((a, b) => new Date(b.detectedAt) - new Date(a.detectedAt)).slice(0, 4);

  // Unified upcoming appointments (both real live appointments and mock nextFollowUp)
  const upcomingList = activeAppointments.length > 0
    ? activeAppointments.slice(0, 6)
    : [...patients]
        .filter((p) => p.nextFollowUp)
        .sort((a, b) => new Date(a.nextFollowUp.date) - new Date(b.nextFollowUp.date))
        .slice(0, 4)
        .map((p) => ({
          id: p.id,
          patientId: p.id,
          patientName: p.name,
          reason: p.nextFollowUp.reason,
          scheduledAt: new Date(p.nextFollowUp.date),
          status: "SCHEDULED",
        }));

  const stats = [
    { label: "Follow-ups Today", value: followUpsToday, icon: CalendarCheck },
    { label: "Checked In Today", value: checkedInToday, icon: Users },
    { label: "Pending Check-ins", value: pendingCheckins, icon: ClipboardList },
    { label: "Total Assigned", value: patients.length, icon: User },
  ];

  return (
    <>
      <Topbar
        title={`${greeting()}, ${user?.name?.split(" ")[0] || "Doctor"}`}
        subtitle="Here's what's happening with your patients and scheduled consults today."
      />
      <main className="flex-1 space-y-8 px-6 py-6">
        {/* Top Attention Section */}
        {needingAttention.length > 0 && (
          <section>
            <div className="mb-3 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="flex h-2.5 w-2.5 rounded-full bg-red-500 animate-pulse" />
                <h2 className="text-base font-semibold text-ink-900">Patients Needing Immediate Attention</h2>
              </div>
              <button
                onClick={() => navigate("/doctor/patients")}
                className="text-sm font-medium text-brand-700 hover:underline"
              >
                View all patients ({patients.length})
              </button>
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              {needingAttention.map((p) => (
                <AttentionCard key={p.id} patient={p} onReview={() => navigate(`/doctor/patients/${p.id}`)} />
              ))}
            </div>
          </section>
        )}

        {/* Today's Care Stats */}
        <section>
          <h2 className="mb-3 text-base font-semibold text-ink-900">Today's Care Overview</h2>
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

        {/* Central AI Clinical Copilot */}
        {patients.length > 0 && (
          <section>
            <div className="mb-3 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Sparkles size={16} className="text-amber-500" />
                <h2 className="text-base font-semibold text-ink-900">AI Clinical Copilot & Patient Reasoning</h2>
              </div>
            </div>
            <DoctorAgentChat patients={patients} />
          </section>
        )}

        {/* Assigned Patients Roster */}
        <section>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-base font-semibold text-ink-900">My Patients ({patients.length})</h2>
            <button
              onClick={() => navigate("/doctor/patients")}
              className="text-sm font-medium text-brand-700 hover:underline flex items-center gap-1"
            >
              Full Roster <ArrowRight size={14} />
            </button>
          </div>
          {patients.length > 0 ? (
            <div className="overflow-hidden rounded-2xl border border-ink-100 bg-white shadow-card">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b border-ink-100 bg-canvas-soft/60 text-xs font-semibold text-ink-500">
                      <th className="px-5 py-3">Patient</th>
                      <th className="px-5 py-3">Phone</th>
                      <th className="px-5 py-3">Status / Risk</th>
                      <th className="px-5 py-3">Latest Check-in</th>
                      <th className="px-5 py-3 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-ink-100">
                    {patients.slice(0, 5).map((p) => (
                      <tr key={p.id} className="hover:bg-canvas-soft/40 transition">
                        <td className="px-5 py-3.5">
                          <p className="font-semibold text-ink-900">{p.name || p.full_name}</p>
                          <p className="text-xs text-ink-400">
                            {p.gender || "Patient"} {p.age ? `• ${p.age} yrs` : ""}
                          </p>
                        </td>
                        <td className="px-5 py-3.5 text-xs text-ink-600 font-mono">
                          {p.phone || p.phone_number || "—"}
                        </td>
                        <td className="px-5 py-3.5">
                          <RiskBadge level={p.riskLevel || "LOW"} size="sm" />
                        </td>
                        <td className="px-5 py-3.5 text-xs text-ink-500">
                          {p.lastCheckIn ? formatRelativeTime(p.lastCheckIn) : "No check-ins yet"}
                        </td>
                        <td className="px-5 py-3.5 text-right">
                          <button
                            onClick={() => navigate(`/doctor/patients/${p.id}`)}
                            className="inline-flex items-center gap-1 rounded-lg bg-brand-50 px-2.5 py-1 text-xs font-semibold text-brand-700 hover:bg-brand-100 transition"
                          >
                            View Chart <ArrowRight size={12} />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : (
            <EmptyState
              title="No patients assigned yet"
              description="Patients registered by reception will appear in your clinical list."
            />
          )}
        </section>

        <div className="grid gap-8 lg:grid-cols-2">
          {/* Recent AI Insights */}
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

          {/* Upcoming Consults & Appointments */}
          <section>
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-base font-semibold text-ink-900">Today's &amp; Upcoming Consultations</h2>
              <span className="text-xs font-semibold text-ink-400">{upcomingList.length} scheduled</span>
            </div>
            {upcomingList.length ? (
              <div className="space-y-3">
                {upcomingList.map((a) => {
                  const targetPatientId = a.patientId || a.patient;
                  const matchedPatient = targetPatientId ? patients.find((p) => String(p.id) === String(targetPatientId)) : null;
                  const patientDisplayName = a.patientName || a.patient_name || matchedPatient?.name || "Patient";
                  const isToday = a.scheduledAt && formatDayLabel(a.scheduledAt) === "Today";

                  return (
                    <div
                      key={a.id}
                      onClick={() => targetPatientId && navigate(`/doctor/patients/${targetPatientId}`)}
                      className="group flex cursor-pointer items-center justify-between rounded-2xl border border-ink-100 bg-white p-4 shadow-card transition hover:border-brand-300 hover:shadow-raised"
                    >
                      <div className="min-w-0 flex items-center gap-3">
                        <div className={`flex h-10 w-10 items-center justify-center rounded-xl transition ${
                          isToday ? "bg-amber-100 text-amber-800 font-bold" : "bg-brand-50 text-brand-700 group-hover:bg-brand-700 group-hover:text-white"
                        }`}>
                          <Calendar size={18} />
                        </div>
                        <div className="min-w-0">
                          <p className="truncate text-sm font-semibold text-ink-900 group-hover:text-brand-700 transition">
                            {patientDisplayName}
                          </p>
                          <p className="truncate text-xs text-ink-500 font-medium">
                            <span className="text-ink-400">Reason:</span> {a.reason || "Scheduled Consultation"}
                          </p>
                        </div>
                      </div>
                      <div className="shrink-0 text-right">
                        <span className={`inline-block rounded-full px-2 py-0.5 text-[11px] font-semibold mb-1 ${
                          isToday ? "bg-amber-100 text-amber-900 border border-amber-300" : "bg-canvas-soft text-ink-600 border border-ink-100"
                        }`}>
                          {formatDayLabel(a.scheduledAt)}
                        </span>
                        <p className="text-xs text-ink-500 flex items-center justify-end gap-1 font-mono">
                          <Clock size={11} /> {formatTime(a.scheduledAt)}
                        </p>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <EmptyState title="No upcoming follow-ups" description="Scheduled appointments from reception will appear here." />
            )}
          </section>
        </div>
      </main>
    </>
  );
}
