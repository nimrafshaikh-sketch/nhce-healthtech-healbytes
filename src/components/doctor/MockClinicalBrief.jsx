import React from "react";
import Button from "../ui/Button";
import Avatar from "../ui/Avatar";
import { Stethoscope, Pill, FlaskConical, FileText } from "lucide-react";
import { useNavigate } from "react-router-dom";

export default function MockClinicalBrief({ patient, onContinue }) {
  const navigate = useNavigate();

  return (
    <div className="mt-8 text-left bg-white p-6 rounded-2xl shadow-card border border-ink-300/15 max-w-xl mx-auto">
      <div className="flex items-center gap-4 border-b border-ink-200 pb-4 mb-4">
        <Avatar name={patient.name} initials={patient.avatarInitials} size="lg" />
        <div>
          <h2 className="text-xl font-bold text-ink-900">{patient.name}</h2>
          <p className="text-sm text-ink-500">ID: {patient.id} • {patient.age} yrs • {patient.gender}</p>
        </div>
      </div>

      <div className="space-y-5">
        <div>
          <h3 className="flex items-center gap-2 text-sm font-bold text-brand-700 uppercase tracking-wide">
            <Stethoscope size={16} /> Patient Summary
          </h3>
          <ul className="mt-2 text-sm text-ink-800 list-disc list-inside space-y-1">
            <li>Previous doctors: 5</li>
            <li>Previous visits: 12</li>
            <li>History: {patient.diagnosis || "Hypertension"}</li>
          </ul>
        </div>

        <div>
          <h3 className="flex items-center gap-2 text-sm font-bold text-brand-700 uppercase tracking-wide">
            <Pill size={16} /> Current Medications
          </h3>
          <ul className="mt-2 text-sm text-ink-800 list-disc list-inside space-y-1">
            <li>Aspirin 75mg</li>
            <li>Atorvastatin 20mg</li>
          </ul>
        </div>

        <div>
          <h3 className="flex items-center gap-2 text-sm font-bold text-brand-700 uppercase tracking-wide">
            <FlaskConical size={16} /> Recent Labs
          </h3>
          <ul className="mt-2 text-sm text-ink-800 list-disc list-inside space-y-1">
            <li>CBC (Normal)</li>
            <li>HbA1c (Borderline)</li>
          </ul>
        </div>

        <div>
          <h3 className="flex items-center gap-2 text-sm font-bold text-brand-700 uppercase tracking-wide">
            <FileText size={16} /> Outstanding
          </h3>
          <p className="mt-2 text-sm text-ink-800 bg-amber-50 p-2 rounded-lg border border-amber-200">
            Follow-up recommended to monitor cholesterol levels. Medication changed recently.
          </p>
        </div>
      </div>

      <div className="mt-6 flex gap-3 pt-4 border-t border-ink-200">
        <Button variant="secondary" className="flex-1" onClick={() => navigate("/doctor/dashboard")}>
          Cancel
        </Button>
        <Button className="flex-1" onClick={onContinue}>
          View Full Profile
        </Button>
      </div>
    </div>
  );
}
