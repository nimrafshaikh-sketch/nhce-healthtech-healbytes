import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight, Check, Circle, Sun, Sunset, Moon, ClipboardCheck } from "lucide-react";
import Avatar from "../../components/ui/Avatar";
import { useAuth } from "../../context/AuthContext";
import { useData } from "../../context/DataContext";
import { formatDayLabel, formatDateTime, formatTime } from "../../utils/dateUtils";
import { getMedications } from "../../api/medication.api";
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
  const { getMedicationsForPatient, getPatientById } = useData();
  const [liveMedications, setLiveMedications] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    let active = true;
    if (!USE_MOCK) {
      getMedications()
        .then((data) => {
          if (active) setLiveMedications(data);
        })
        .catch(console.error);
    }
    return () => {
      active = false;
    };
  }, []);

  const patient = getPatientById(user?.id) || user || {};

  const order = { MORNING: 0, AFTERNOON: 1, EVENING: 2 };
  const rawMeds = liveMedications !== null ? liveMedications : getMedicationsForPatient(patient.id);
  const medications = [...rawMeds].sort(
    (a, b) => order[a.timeOfDay] - order[b.timeOfDay]
  );

  const checkedInToday = patient.lastCheckIn && formatDayLabel(patient.lastCheckIn) === "Today";
  const status = STATUS_COPY[patient.riskLevel] || STATUS_COPY.LOW;

  return (
    <div className="flex-1 px-5 pb-6 pt-8">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-lg font-semibold text-ink-900">
            {greeting()}, {user.name.split(" ")[0]} 👋
          </p>
          <p className="text-sm text-ink-500">Let's take care of your health today.</p>
        </div>
        <Avatar name={user.name} initials={user.avatarInitials} />
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
        <h2 className="mb-3 text-sm font-semibold text-ink-900">Today</h2>
        <div className="space-y-2">
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

          {medications.map((m) => {
            const Icon = TIME_ICON[m.timeOfDay] || Sun;
            const done = m.status === "TAKEN";
            return (
              <div key={m.id} className="flex items-center gap-3 rounded-2xl border border-ink-300/15 bg-white p-3.5 shadow-card">
                <div className="flex h-9 w-9 items-center justify-center rounded-full bg-canvas-soft text-ink-500">
                  <Icon size={16} />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-ink-900">{m.name}</p>
                  <p className="truncate text-xs text-ink-500">
                    {m.dosage} · {m.instructions}
                  </p>
                </div>
                {done ? <Check size={16} className="text-risk-low" /> : <Circle size={14} className="text-ink-300" />}
              </div>
            );
          })}
        </div>
      </div>

      {patient.nextFollowUp && (
        <div className="mt-7 rounded-2xl border border-ink-300/15 bg-white p-4 shadow-card">
          <p className="text-xs font-semibold uppercase tracking-wide text-ink-300">Next Follow-up</p>
          <div className="mt-2 flex items-center justify-between">
            <div>
              <p className="text-sm font-semibold text-ink-900">{patient.nextFollowUp.doctorName}</p>
              <p className="text-xs text-ink-500">{patient.nextFollowUp.reason}</p>
            </div>
            <div className="text-right">
              <p className="text-xs font-medium text-ink-700">{formatDayLabel(patient.nextFollowUp.date)}</p>
              <p className="text-xs text-ink-300">{formatTime(patient.nextFollowUp.date)}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
