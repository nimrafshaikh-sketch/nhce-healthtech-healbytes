import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, CalendarDays, CheckCircle2, XCircle } from "lucide-react";
import EmptyState from "../../components/ui/EmptyState";
import { getMyAppointments, confirmAppointment, cancelAppointment } from "../../api/appointment.api";

// Previously there was no patient-facing appointments screen at all (no
// route, no nav entry - see AppRouter.jsx history). Appointments booked by
// a doctor or receptionist (apps.appointments) were only ever visible on
// their side; a patient had no way to see, confirm, or cancel their own.
// This is the real, working implementation - getMyAppointments/
// confirmAppointment/cancelAppointment call the actual backend endpoints
// (GET /appointments/, POST /appointments/:id/confirm|cancel/) that were
// already correctly scoped to "my own appointments only" server-side.

const STATUS_TONE = {
  SCHEDULED: "bg-amber-50 text-amber-700",
  CONFIRMED: "bg-risk-low-bg text-risk-low",
  COMPLETED: "bg-ink-900/5 text-ink-500",
  CANCELLED: "bg-risk-high-bg text-risk-high",
  NO_SHOW: "bg-risk-high-bg text-risk-high",
};

export default function Appointments() {
  const navigate = useNavigate();
  const [appointments, setAppointments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actioningId, setActioningId] = useState(null);

  function load() {
    setLoading(true);
    setError(null);
    getMyAppointments()
      .then((data) => setAppointments(data.sort((a, b) => (b.scheduledAt || 0) - (a.scheduledAt || 0))))
      .catch((err) => setError(err.message || "Could not load your appointments."))
      .finally(() => setLoading(false));
  }

  useEffect(load, []);

  async function handleConfirm(id) {
    setActioningId(id);
    try {
      await confirmAppointment(id);
      load();
    } catch (err) {
      setError(err.message || "Could not confirm this appointment.");
    } finally {
      setActioningId(null);
    }
  }

  async function handleCancel(id) {
    setActioningId(id);
    try {
      await cancelAppointment(id);
      load();
    } catch (err) {
      setError(err.message || "Could not cancel this appointment.");
    } finally {
      setActioningId(null);
    }
  }

  return (
    <div className="flex-1 px-5 pb-6 pt-8">
      <div className="mb-2 flex items-center gap-3">
        <button onClick={() => navigate(-1)} aria-label="Back" className="rounded-full p-1.5 text-ink-500 hover:bg-canvas-soft">
          <ArrowLeft size={18} />
        </button>
        <h1 className="text-lg font-semibold text-ink-900">Appointments</h1>
      </div>
      <p className="mb-6 text-sm text-ink-500">Appointments booked with your care team.</p>

      {error && (
        <div className="mb-4 rounded-xl border border-risk-high/30 bg-risk-high-bg px-4 py-3 text-sm text-risk-high">
          {error}
        </div>
      )}

      {loading ? (
        <div className="py-12 text-center text-sm text-ink-500">Loading…</div>
      ) : appointments.length === 0 ? (
        <EmptyState title="No appointments yet" description="Your care team hasn't booked anything for you yet." />
      ) : (
        <div className="space-y-3">
          {appointments.map((appt) => (
            <div key={appt.id} className="rounded-2xl border border-ink-300/15 bg-white p-4 shadow-card">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-3">
                  <div className="flex h-9 w-9 items-center justify-center rounded-full bg-canvas-soft text-ink-500">
                    <CalendarDays size={16} />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-ink-900">{appt.doctorName || "Your doctor"}</p>
                    {appt.reason && <p className="text-xs text-ink-500">{appt.reason}</p>}
                    <p className="mt-1 text-xs text-ink-500">
                      {appt.scheduledAt
                        ? appt.scheduledAt.toLocaleString(undefined, {
                            month: "short",
                            day: "numeric",
                            hour: "numeric",
                            minute: "2-digit",
                          })
                        : appt.timeLabel || "Time TBD"}
                    </p>
                  </div>
                </div>
                <span className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-semibold uppercase tracking-wide ${STATUS_TONE[appt.status] || "bg-ink-900/5 text-ink-500"}`}>
                  {appt.status.replace("_", " ")}
                </span>
              </div>

              {appt.status === "SCHEDULED" && (
                <div className="mt-3 flex gap-2 border-t border-ink-300/10 pt-3">
                  <button
                    onClick={() => handleConfirm(appt.id)}
                    disabled={actioningId === appt.id}
                    className="flex flex-1 items-center justify-center gap-1.5 rounded-xl bg-brand-700 py-2 text-sm font-medium text-white transition hover:bg-brand-800 disabled:opacity-50"
                  >
                    <CheckCircle2 size={15} /> Confirm
                  </button>
                  <button
                    onClick={() => handleCancel(appt.id)}
                    disabled={actioningId === appt.id}
                    className="flex flex-1 items-center justify-center gap-1.5 rounded-xl border border-ink-300/25 py-2 text-sm font-medium text-ink-600 transition hover:bg-canvas-soft disabled:opacity-50"
                  >
                    <XCircle size={15} /> Cancel
                  </button>
                </div>
              )}
              {appt.status === "CONFIRMED" && (
                <div className="mt-3 border-t border-ink-300/10 pt-3">
                  <button
                    onClick={() => handleCancel(appt.id)}
                    disabled={actioningId === appt.id}
                    className="flex w-full items-center justify-center gap-1.5 rounded-xl border border-ink-300/25 py-2 text-sm font-medium text-ink-600 transition hover:bg-canvas-soft disabled:opacity-50"
                  >
                    <XCircle size={15} /> Cancel
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
