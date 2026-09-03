import React from "react";
import { Sun, Sunset, Moon } from "lucide-react";
import MedicationCard from "../../components/healthcare/MedicationCard";
import EmptyState from "../../components/ui/EmptyState";
import { useAuth } from "../../context/AuthContext";
import { useData } from "../../context/DataContext";

const GROUPS = [
  { key: "MORNING", label: "Morning", icon: Sun },
  { key: "AFTERNOON", label: "Afternoon", icon: Sunset },
  { key: "EVENING", label: "Evening", icon: Moon },
];

export default function Medicines() {
  const { user } = useAuth();
  const { getMedicationsForPatient, markMedicationStatus } = useData();
  const medications = getMedicationsForPatient(user.id);

  return (
    <div className="flex-1 px-5 pb-6 pt-8">
      <h1 className="text-lg font-semibold text-ink-900">Medicines</h1>
      <p className="mt-1 text-sm text-ink-500">Your schedule for today.</p>

      <div className="mt-6 space-y-7">
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
        {!medications.length && (
          <EmptyState title="No medicines scheduled" description="Your doctor hasn't added any medications yet." />
        )}
      </div>
    </div>
  );
}
