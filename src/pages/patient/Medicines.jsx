import React, { useState, useEffect, useCallback } from "react";
import { Sun, Sunset, Moon, FileText, CheckCircle2, History } from "lucide-react";
import MedicationCard from "../../components/healthcare/MedicationCard";
import EmptyState from "../../components/ui/EmptyState";
import { useAuth } from "../../context/AuthContext";
import { useData } from "../../context/DataContext";
import { getMedications } from "../../api/medication.api";
import { getPrescriptionsForPatient } from "../../api/prescription.api";
import { USE_MOCK } from "../../api/client";

const GROUPS = [
  { key: "MORNING", label: "Morning", icon: Sun, subtitle: "8:00 AM" },
  { key: "AFTERNOON", label: "Afternoon", icon: Sunset, subtitle: "1:00 PM" },
  { key: "EVENING", label: "Evening", icon: Moon, subtitle: "8:00 PM" },
];

export default function Medicines() {
  const { user } = useAuth();
  const { getMedicationsForPatient, markMedicationStatus } = useData();
  const [liveMedications, setLiveMedications] = useState(null);
  const [prescriptions, setPrescriptions] = useState([]);

  const loadData = useCallback(() => {
    if (!USE_MOCK) {
      getMedications()
        .then((data) => {
          setLiveMedications(Array.isArray(data) ? data : []);
        })
        .catch(console.error);
    }
    if (user?.id) {
      getPrescriptionsForPatient(user.id)
        .then((data) => {
          setPrescriptions(Array.isArray(data) ? data : []);
        })
        .catch(console.error);
    }
  }, [user?.id]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleMarkStatus = async (medicationId, status) => {
    const now = new Date();
    setLiveMedications((prev) => {
      const source = prev !== null ? prev : getMedicationsForPatient(user?.id);
      return source.map((m) =>
        m.id === medicationId ? { ...m, status, takenAt: status === "TAKEN" ? now : null } : m
      );
    });
    try {
      await markMedicationStatus(medicationId, status);
    } catch (e) {
      console.error("Error marking status:", e);
    }
  };

  const belongsToSlot = (m, slotKey) => {
    if (m.reminder_times && m.reminder_times.length > 0) {
      return m.reminder_times.some((t) => {
        const h = parseInt(t.split(":")[0], 10);
        if (slotKey === "MORNING") return h >= 4 && h < 12;
        if (slotKey === "AFTERNOON") return h >= 12 && h < 17;
        if (slotKey === "EVENING") return h >= 17 || h < 4;
        return false;
      });
    }
    const freq = (m.frequency || "").toLowerCase();
    if (freq.includes("twice") || freq === "twice_daily") {
      return slotKey === "MORNING" || slotKey === "EVENING";
    }
    if (freq.includes("three") || freq === "three_times_daily") {
      return true;
    }
    return m.timeOfDay === slotKey || slotKey === "MORNING";
  };

  const allMeds = liveMedications !== null ? liveMedications : getMedicationsForPatient(user?.id) || [];

  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const activeMeds = allMeds.filter((m) => {
    if (m.is_active === false) return false;
    const endDateStr = m.endDate || m.end_date;
    if (endDateStr) {
      const end = new Date(endDateStr);
      end.setHours(0, 0, 0, 0);
      if (end < today) return false;
    }
    return true;
  });

  const completedMeds = allMeds.filter((m) => {
    if (m.is_active === false) return true;
    const endDateStr = m.endDate || m.end_date;
    if (endDateStr) {
      const end = new Date(endDateStr);
      end.setHours(0, 0, 0, 0);
      if (end < today) return true;
    }
    return false;
  });

  return (
    <div className="flex-1 px-5 pb-6 pt-8">
      <h1 className="text-lg font-semibold text-ink-900">Medicines & Prescriptions</h1>
      <p className="mt-1 text-sm text-ink-500">Your current medications and official prescriptions.</p>

      {prescriptions.length > 0 && (
        <div className="mt-6">
          <div className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-ink-300">
            <FileText size={14} /> Official Prescriptions
          </div>
          <div className="space-y-4">
            {prescriptions.map((p) => (
              <div key={p.id} className="bg-white rounded-xl shadow-sm border border-brand-200 p-4">
                <div className="flex justify-between items-start mb-2">
                  <h3 className="font-bold text-brand-800">Prescription</h3>
                  <span className="text-xs text-ink-400">{new Date(p.date || p.created_at || Date.now()).toLocaleDateString()}</span>
                </div>
                <div className="space-y-2 mt-3">
                  {(p.medications || []).map((m, idx) => (
                    <div key={idx} className="bg-brand-50 p-3 rounded-lg border border-brand-100">
                      <div className="flex items-center justify-between">
                        <p className="font-bold text-brand-900">{m.name} - {m.dosage}</p>
                        {(m.prescribed_by_name || p.doctor_name) && (
                          <span className="text-[11px] font-medium text-brand-800 bg-brand-100/80 border border-brand-200 px-2 py-0.5 rounded-full">
                            Dr. {m.prescribed_by_name || p.doctor_name}
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-brand-700 mt-1">
                        {m.frequency} {m.duration ? `for ${m.duration}` : ""} <br />
                        <span className="text-xs opacity-80">{m.instructions || "Take as prescribed"}</span>
                      </p>
                      {m.reminder_times && m.reminder_times.length > 0 && (
                        <div className="mt-2">
                          <span className="text-[11px] font-medium text-brand-700 bg-white border border-brand-200/80 px-2 py-0.5 rounded-full inline-flex items-center gap-1 shadow-xs">
                            ⏰ Scheduled: {m.reminder_times.map((t) => {
                              const [h, min] = t.split(":");
                              const hour = parseInt(h, 10);
                              const ampm = hour >= 12 ? "PM" : "AM";
                              const hour12 = hour % 12 || 12;
                              return `${hour12}:${min} ${ampm}`;
                            }).join(", ")}
                          </span>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Active Daily Schedule */}
      <div className="mt-8 space-y-7">
        <h2 className="text-sm font-semibold text-ink-900 mb-4">Daily Schedule</h2>
        {GROUPS.map(({ key, label, subtitle, icon: Icon }) => {
          const items = activeMeds.filter((m) => belongsToSlot(m, key));
          if (!items.length) return null;
          return (
            <div key={key}>
              <div className="mb-3 flex items-center justify-between text-xs font-semibold uppercase tracking-wide text-ink-500">
                <div className="flex items-center gap-2">
                  <Icon size={14} className="text-brand-600" /> {label}
                </div>
                <span className="text-[11px] text-ink-400 font-normal">⏰ {subtitle}</span>
              </div>
              <div className="space-y-2.5">
                {items.map((m) => (
                  <MedicationCard
                    key={`${m.id}-${key}`}
                    medication={m}
                    onMarkTaken={() => handleMarkStatus(m.id, "TAKEN")}
                    onMarkMissed={() => handleMarkStatus(m.id, "MISSED")}
                  />
                ))}
              </div>
            </div>
          );
        })}
        {!activeMeds.length && !prescriptions.length && (
          <EmptyState title="No active medicines" description="Your active course is completed or no medications scheduled." />
        )}
      </div>

      {/* Completed / Past Medication Courses */}
      {completedMeds.length > 0 && (
        <div className="mt-10 border-t border-ink-100 pt-6">
          <div className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-ink-400">
            <History size={14} /> Completed Medication Courses ({completedMeds.length})
          </div>
          <div className="space-y-2.5 opacity-75">
            {completedMeds.map((m) => (
              <MedicationCard
                key={m.id}
                medication={m}
                readOnly={true}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
