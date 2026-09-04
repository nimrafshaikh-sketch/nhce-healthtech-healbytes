import React from "react";
import { Stethoscope, Pill, FlaskConical, FileText, ScanLine } from "lucide-react";
import Button from "../ui/Button";
import Avatar from "../ui/Avatar";

// Renders the REAL response from POST /api/qr/verify/ (or its mock-mode
// equivalent, api/qr.api.js::verifyQr) - patient, recent_medications,
// recent_checkins, clinical_brief. This replaces the old MockClinicalBrief,
// which showed hardcoded placeholder text ("Aspirin 75mg", "Previous
// doctors: 5") regardless of which patient was actually scanned (Part 4/5
// root cause) - every value here is traced back to the authorized backend
// payload, never invented client-side.
//
// Accepts either the live Django shape (full_name, date_of_birth) or the
// mock-mode shape (name, age) for the patient object, since the two aren't
// unified yet (see DataContext live-wiring).
function getName(patient) {
  return patient.full_name || patient.name || "Unknown patient";
}
function getAge(patient) {
  if (patient.age != null) return patient.age;
  if (patient.date_of_birth) {
    const dob = new Date(patient.date_of_birth);
    if (!Number.isNaN(dob.getTime())) {
      const diff = Date.now() - dob.getTime();
      return Math.floor(diff / (365.25 * 24 * 60 * 60 * 1000));
    }
  }
  return null;
}
function initialsOf(name) {
  return name.split(" ").filter(Boolean).slice(0, 2).map((p) => p[0].toUpperCase()).join("");
}

export default function ClinicalBriefCard({ data, isPrimaryDoctor, onContinue, onScanAnother }) {
  const { patient, recent_medications: medications = [], recent_checkins: checkins = [], clinical_brief: brief } = data;
  const name = getName(patient);
  const age = getAge(patient);

  return (
    <div className="mx-auto mt-8 max-w-xl rounded-2xl border border-ink-300/15 bg-white p-6 text-left shadow-card">
      <div className="mb-4 flex items-center gap-4 border-b border-ink-200 pb-4">
        <Avatar name={name} initials={patient.avatarInitials || initialsOf(name)} size="lg" />
        <div>
          <h2 className="text-xl font-bold text-ink-900">{name}</h2>
          <p className="text-sm text-ink-500">
            ID: {patient.id}
            {age != null ? ` • ${age} yrs` : ""}
            {patient.gender ? ` • ${patient.gender}` : ""}
          </p>
        </div>
        <span className="ml-auto rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700">
          {isPrimaryDoctor ? "Standing access" : "Time-limited consult access"}
        </span>
      </div>

      <div className="space-y-5">
        {brief?.narrative && (
          <div>
            <h3 className="flex items-center gap-2 text-sm font-bold uppercase tracking-wide text-brand-700">
              <Stethoscope size={16} /> Clinical Summary
            </h3>
            <p className="mt-2 text-sm text-ink-800">{brief.narrative}</p>
            {brief.current_conditions?.length > 0 && (
              <p className="mt-1 text-xs text-ink-500">
                Conditions: {brief.current_conditions.join(", ")}
              </p>
            )}
          </div>
        )}

        <div>
          <h3 className="flex items-center gap-2 text-sm font-bold uppercase tracking-wide text-brand-700">
            <Pill size={16} /> Current Medications
          </h3>
          {medications.length ? (
            <ul className="mt-2 list-inside list-disc space-y-1 text-sm text-ink-800">
              {medications.map((m) => (
                <li key={m.id}>
                  {m.name} {m.dosage} - {m.frequency}
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-2 text-sm text-ink-400">No active medications on file.</p>
          )}
        </div>

        <div>
          <h3 className="flex items-center gap-2 text-sm font-bold uppercase tracking-wide text-brand-700">
            <FlaskConical size={16} /> Recent Labs
          </h3>
          {brief?.recent_labs?.length ? (
            <ul className="mt-2 list-inside list-disc space-y-1 text-sm text-ink-800">
              {brief.recent_labs.map((l, i) => (
                <li key={i}>
                  {l.test_name}: {l.latest_value} ({l.date})
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-2 text-sm text-ink-400">No lab results on file.</p>
          )}
        </div>

        <div>
          <h3 className="flex items-center gap-2 text-sm font-bold uppercase tracking-wide text-brand-700">
            <FileText size={16} /> Recent Check-ins
          </h3>
          {checkins.length ? (
            <ul className="mt-2 list-inside list-disc space-y-1 text-sm text-ink-800">
              {checkins.slice(0, 3).map((c, i) => (
                <li key={c.id || i}>
                  {c.checkin_date || c.date}: {c.ai_risk_level || c.riskLevel || "unrated"}
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-2 text-sm text-ink-400">No recent check-ins.</p>
          )}
        </div>
      </div>

      {!isPrimaryDoctor && (
        <p className="mt-4 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
          You are not this patient's primary doctor. This consult summary is the full extent of your
          time-limited access - it will not appear in your patient list, and it expires automatically.
        </p>
      )}

      <div className="mt-6 flex gap-3 border-t border-ink-200 pt-4">
        <Button variant="secondary" className="flex-1" leftIcon={<ScanLine size={15} />} onClick={onScanAnother}>
          Scan Another
        </Button>
        {isPrimaryDoctor && (
          <Button className="flex-1" onClick={onContinue}>
            View Full Profile
          </Button>
        )}
      </div>
    </div>
  );
}
