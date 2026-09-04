import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight, Check, CheckCircle2, Circle, Sun, Sunset, Moon, ClipboardCheck, Clock } from "lucide-react";
import Avatar from "../../components/ui/Avatar";
import NotificationBell from "../../components/layout/NotificationBell";
import { useAuth } from "../../context/AuthContext";
import { useData } from "../../context/DataContext";
import { formatDayLabel, formatDateTime, formatTime } from "../../utils/dateUtils";
import { getMedications } from "../../api/medication.api";
import { getMyAppointments } from "../../api/appointment.api";
import { USE_MOCK } from "../../api/client";

const STATUS_COPY = {
  LOW: {
    title: "You're doing well today",
    note: "Your care team will continue monitoring your progress.",
  },
  MEDIUM: {
    title: "We noticed something worth monitoring",
    note: "Your care team has been informed and is keeping an eye on things.",
  },
  HIGH: {
    title: "Your care team has been notified",
    note: "Please follow any instructions from your healthcare provider.",
  },
};

const TIME_ICON = { MORNING: Sun, AFTERNOON: Sunset, EVENING: Moon };
const RISK_LABEL = { LOW: "Low Risk", MEDIUM: "Medium Risk", HIGH: "High Risk" };
const RISK_TONE = {
  LOW: "bg-risk-low-bg text-risk-low",
  MEDIUM: "bg-risk-medium-bg text-risk-medium",
  HIGH: "bg-risk-high-bg text-risk-high",
};

function greeting() {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

export default function PatientHome() {
  const { user } = useAuth();
  const { getMedicationsForPatient, getPatientById, markMedicationStatus } = useData();
  const [liveMedications, setLiveMedications] = useState(null);
  const [upcomingAppointment, setUpcomingAppointment] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    let active = true;
    if (!USE_MOCK) {
      getMedications()
        .then((data) => {
          if (active) setLiveMedications(Array.isArray(data) ? data : []);
        })
        .catch(console.error);

      getMyAppointments()
        .then((appts) => {
          if (!active) return;
          const upcoming = (appts || [])
            .filter((a) => ["SCHEDULED", "CONFIRMED"].includes(a.status) && a.scheduledAt && a.scheduledAt > new Date())
            .sort((a, b) => a.scheduledAt - b.scheduledAt)[0];
          setUpcomingAppointment(upcoming || null);
        })
        .catch(console.error);
    }
    return () => {
      active = false;
    };
  }, []);

  const patient = getPatientById(user?.id) || user || {};

  const handleToggleTake = async (e, medicationId, currentStatus) => {
    e.stopPropagation();
    const newStatus = currentStatus === "TAKEN" ? "PENDING" : "TAKEN";
    const now = new Date();
    setLiveMedications((prev) => {
      const source = prev !== null ? prev : getMedicationsForPatient(patient.id);
      return source.map((m) =>
        m.id === medicationId ? { ...m, status: newStatus, takenAt: newStatus === "TAKEN" ? now : null } : m
      );
    });
    try {
      await markMedicationStatus(medicationId, newStatus);
    } catch (err) {
      console.error("Error marking status in Home:", err);
    }
  };

  const rawMeds = liveMedications !== null ? liveMedications : getMedicationsForPatient(patient.id);

  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const activeMeds = (rawMeds || []).filter((m) => {
    if (m.is_active === false) return false;
    const endDateStr = m.endDate || m.end_date;
    if (endDateStr) {
      const end = new Date(endDateStr);
      end.setHours(0, 0, 0, 0);
      if (end < today) return false;
    }
    return true;
  });

  // Expand multi-dose medications into daily schedule slots
  const scheduledDoses = [];
  activeMeds.forEach((m) => {
    const times = (m.reminder_times && m.reminder_times.length > 0)
      ? m.reminder_times
      : (m.frequency === "twice_daily" ? ["08:00", "20:00"] : ["08:00"]);

    times.forEach((t) => {
      const [h, min] = t.split(":");
      const hour = parseInt(h, 10);
      const ampm = hour >= 12 ? "PM" : "AM";
      const hour12 = hour % 12 || 12;
      const slotTimeStr = `${hour12}:${min} ${ampm}`;
      const slotType = hour < 12 ? "MORNING" : hour < 17 ? "AFTERNOON" : "EVENING";

      scheduledDoses.push({
        ...m,
        slotKey: `${m.id}-${t}`,
        slotTimeStr,
        slotType,
        hourSort: hour * 60 + parseInt(min, 10),
      });
    });
  });

  scheduledDoses.sort((a, b) => a.hourSort - b.hourSort);

  const checkedInToday = patient.lastCheckIn && formatDayLabel(patient.lastCheckIn) === "Today";
  const status = STATUS_COPY[patient.riskLevel] || STATUS_COPY.LOW;

  return (
    <div className="flex-1 px-5 pb-6 pt-8">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-lg font-semibold text-ink-900">
            {greeting()}, {user.name ? user.name.split(" ")[0] : "Patient"} 👋
          </p>
          <p className="text-sm text-ink-500">Let's take care of your health today.</p>
        </div>
        <div className="flex items-center gap-2">
          <NotificationBell />
          <Avatar name={user.name || "Patient"} initials={user.avatarInitials} />
        </div>
      </div>

      <div className="mt-6 rounded-2xl border border-ink-300/15 bg-white p-5 shadow-card">
        <p className="text-xs font-semibold uppercase tracking-wide text-ink-300">Your Health Status</p>
        <p className="mt-1.5 text-lg font-semibold text-ink-900">{status.title}</p>
        <span
          className={`mt-2 inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold uppercase tracking-wide ${
            RISK_TONE[patient.riskLevel] || RISK_TONE.LOW
          }`}
        >
          {RISK_LABEL[patient.riskLevel] || RISK_LABEL.LOW}
        </span>
        <p className="mt-2 text-sm text-ink-600">{status.note}</p>
        <p className="mt-3 text-xs text-ink-300">
          Last check-in: {patient.lastCheckIn ? formatDateTime(patient.lastCheckIn) : "Not yet"}
        </p>
      </div>

      {!checkedInToday && (
        <button
          onClick={() => navigate("/patient/check-in")}
          className="mt-5 block w-full rounded-2xl bg-brand-700 p-5 text-left text-white shadow-raised transition hover:bg-brand-800"
        >
          <p className="text-base font-semibold">How are you feeling today?</p>
          <p className="mt-1 text-sm text-brand-100">A quick check-in helps your care team monitor your recovery.</p>
          <span className="mt-3 inline-flex items-center gap-1.5 text-sm font-semibold">
            Start Daily Check-in <ArrowRight size={15} />
          </span>
        </button>
      )}

      <div className="mt-7">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-ink-900">Today's Schedule</h2>
          <button
            type="button"
            onClick={() => navigate("/patient/medicines")}
            className="text-xs font-semibold text-brand-700 hover:text-brand-800"
          >
            View all medications &rarr;
          </button>
        </div>

        <div className="space-y-2.5">
          <div className="flex items-center gap-3 rounded-2xl border border-ink-300/15 bg-white p-3.5 shadow-card">
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-canvas-soft text-ink-500">
              <ClipboardCheck size={16} />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-ink-900">Daily Health Check-in</p>
              <p className="text-xs text-ink-500">{checkedInToday ? "Completed" : "Pending"}</p>
            </div>
            {checkedInToday ? (
              <Check size={16} className="text-risk-low" />
            ) : (
              <Circle size={14} className="text-ink-300" />
            )}
          </div>

          {scheduledDoses.map((dose) => {
            const Icon = TIME_ICON[dose.slotType] || Sun;
            const isDone = dose.status === "TAKEN";

            return (
              <div
                key={dose.slotKey}
                onClick={() => navigate("/patient/medicines")}
                className={`flex cursor-pointer items-center gap-3 rounded-2xl border p-3.5 shadow-card transition ${
                  isDone ? "bg-emerald-50/40 border-emerald-200" : "bg-white border-ink-300/15 hover:border-brand-300"
                }`}
              >
                <div className={`flex h-9 w-9 items-center justify-center rounded-full ${
                  isDone ? "bg-emerald-100 text-emerald-700" : "bg-canvas-soft text-ink-500"
                }`}>
                  <Icon size={16} />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between gap-2">
                    <p className="truncate text-sm font-semibold text-ink-900">{dose.name} - {dose.dosage}</p>
                    <span className="shrink-0 text-[10px] font-semibold text-brand-700 bg-brand-50 border border-brand-200/70 px-2 py-0.5 rounded-full flex items-center gap-1">
                      <Clock size={10} /> ⏰ {dose.slotTimeStr}
                    </span>
                  </div>
                  <p className="truncate text-xs text-ink-500 mt-0.5">
                    {dose.instructions || "Take as prescribed"}
                  </p>
                  {isDone && (
                    <p className="text-[11px] font-semibold text-emerald-700 mt-1 flex items-center gap-1">
                      <CheckCircle2 size={12} /> Taken at {dose.takenAt ? formatTime(dose.takenAt) : dose.slotTimeStr}
                    </p>
                  )}
                </div>

                <button
                  type="button"
                  title={isDone ? "Dose taken" : "Mark as taken"}
                  onClick={(e) => handleToggleTake(e, dose.id, dose.status)}
                  className={`p-2 rounded-xl border transition ${
                    isDone
                      ? "bg-emerald-600 text-white border-emerald-600 hover:bg-emerald-700"
                      : "bg-white text-ink-400 border-ink-200 hover:border-brand-500 hover:text-brand-600"
                  }`}
                >
                  <Check size={16} strokeWidth={2.5} />
                </button>
              </div>
            );
          })}
        </div>
      </div>

      {(upcomingAppointment || (USE_MOCK && patient.nextFollowUp)) && (
        <button
          onClick={() => navigate("/patient/appointments")}
          className="mt-7 block w-full rounded-2xl border border-ink-300/15 bg-white p-4 text-left shadow-card"
        >
          <p className="text-xs font-semibold uppercase tracking-wide text-ink-300">Next Follow-up</p>
          <div className="mt-2 flex items-center justify-between">
            <div>
              <p className="text-sm font-semibold text-ink-900">
                {upcomingAppointment ? upcomingAppointment.doctorName : patient.nextFollowUp.doctorName}
              </p>
              <p className="text-xs text-ink-500">
                {upcomingAppointment ? upcomingAppointment.reason : patient.nextFollowUp.reason}
              </p>
            </div>
            <div className="text-right">
              <p className="text-xs font-medium text-ink-700">
                {formatDayLabel(upcomingAppointment ? upcomingAppointment.scheduledAt : patient.nextFollowUp.date)}
              </p>
              <p className="text-xs text-ink-300">
                {formatTime(upcomingAppointment ? upcomingAppointment.scheduledAt : patient.nextFollowUp.date)}
              </p>
            </div>
          </div>
        </button>
      )}

      {!USE_MOCK && (
        <button
          onClick={() => navigate("/patient/appointments")}
          className="mt-3 block w-full text-center text-sm font-medium text-brand-700 hover:underline"
        >
          View all appointments
        </button>
      )}
    </div>
  );
}
