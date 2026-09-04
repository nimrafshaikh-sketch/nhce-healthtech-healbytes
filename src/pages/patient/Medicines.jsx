import React, { useState, useEffect } from "react";
import { Sun, Sunset, Moon, FileText } from "lucide-react";
import MedicationCard from "../../components/healthcare/MedicationCard";
import EmptyState from "../../components/ui/EmptyState";
import { useAuth } from "../../context/AuthContext";
import { useData } from "../../context/DataContext";
import { getMedications } from "../../api/medication.api";
import { getPrescriptionsForPatient } from "../../api/prescription.api";
import { USE_MOCK } from "../../api/client";

const GROUPS = [
  { key: "MORNING", label: "Morning", icon: Sun },
  { key: "AFTERNOON", label: "Afternoon", icon: Sunset },
  { key: "EVENING", label: "Evening", icon: Moon },
];

export default function Medicines() {
  const { user } = useAuth();
  const { getMedicationsForPatient, markMedicationStatus } = useData();
  const [liveMedications, setLiveMedications] = useState(null);
  const [prescriptions, setPrescriptions] = useState([]);

  useEffect(() => {
    let active = true;
    if (!USE_MOCK) {
      getMedications()
        .then((data) => {
          if (active) setLiveMedications(data);
        })
        .catch(console.error);
    }
    if (user?.id) {
      getPrescriptionsForPatient(user.id)
        .then((data) => {
          if (active) setPrescriptions(Array.isArray(data) ? data : []);
        })
        .catch(console.error);
    }
    return () => {
      active = false;
    };
  }, [user?.id]);

  const medications = liveMedications !== null ? liveMedications : getMedicationsForPatient(user?.id);

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
                      <p className="font-bold text-brand-900">{m.name} - {m.dosage}</p>
                      <p className="text-sm text-brand-700 mt-1">
                        {m.frequency} {m.duration ? `for ${m.duration}` : ""} <br />
                        <span className="text-xs opacity-80">{m.instructions}</span>
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="mt-8 space-y-7">
        <h2 className="text-sm font-semibold text-ink-900 mb-4">Daily Schedule</h2>
        {GROUPS.map(({ key, label, icon: Icon }) => {
          const items = medications.filter((m) => m.timeOfDay === key);
          if (!items.length) return null;
          return (
            <div key={key}>
              <div className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-ink-300">
                <Icon size={14} /> {label}
              </div>
              <div className="space-y-2.5">
                {items.map((m) => (
                  <MedicationCard
                    key={m.id}
                    medication={m}
                    onMarkTaken={() => markMedicationStatus(m.id, "TAKEN")}
                    onMarkMissed={() => markMedicationStatus(m.id, "MISSED")}
                  />
                ))}
              </div>
            </div>
          );
        })}
        {!medications.length && !prescriptions.length && (
          <EmptyState title="No medicines scheduled" description="Your doctor hasn't added any medications yet." />
        )}
      </div>
    </div>
  );
}
