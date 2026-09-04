import { apiFetch, USE_MOCK, mockDelay } from "./client";
import { ENDPOINTS } from "./endpoints";
import { createPatientRecord, getInitials } from "../services/mockService";

// --- Live-mode shape adapter -------------------------------------------
// Django's Patient model/serializer (apps.patients.serializers) uses its
// own field names (full_name, date_of_birth, phone_number, medical_notes,
// caretaker_name/...) and has no concept of the mock UI's derived/demo
// fields (riskLevel, riskScore, condition, diagnosis, medicationAdherencePct,
// invitationCode, avatarInitials...) - those are computed elsewhere (AI
// engine risk scoring, checkins, invitations) or are mock-only narrative
// flavor. This adapter normalizes a raw Django Patient into the shape the
// existing components already read, WITHOUT fabricating clinical claims:
// fields with no real backend source are left null/sensible-default rather
// than invented, and every original Django field is preserved too (so
// code that needs the real `doctor` id, `medical_notes`, etc. still works).
function normalizePatient(raw) {
  if (!raw) return raw;
  const age = raw.date_of_birth ? computeAge(raw.date_of_birth) : raw.age ?? null;
  return {
    ...raw,
    id: raw.id,
    name: raw.full_name || raw.name,
    age,
    gender: raw.gender ? raw.gender[0].toUpperCase() + raw.gender.slice(1) : raw.gender,
    phone: raw.phone_number || raw.phone || "",
    notes: raw.medical_notes || raw.notes || "",
    caretaker: raw.caretaker_name || raw.caretaker
      ? {
          name: raw.caretaker_name ?? raw.caretaker?.name ?? "",
          relationship: raw.caretaker_relationship ?? raw.caretaker?.relationship ?? "",
          phone: raw.caretaker_phone_number ?? raw.caretaker?.phone ?? "",
        }
      : raw.caretaker,
    avatarInitials: raw.avatarInitials || getInitials(raw.full_name || raw.name || ""),
    // No backend equivalent yet for these demo/derived fields - left as
    // honest defaults (not fabricated data) until AI risk scoring is
    // surfaced on the Patient record itself.
    riskLevel: raw.riskLevel ?? "LOW",
    riskScore: raw.riskScore ?? 0,
    condition: raw.condition ?? "",
    diagnosis: raw.diagnosis ?? "",
    allergies: raw.allergies ?? "",
    medicationAdherencePct: raw.medicationAdherencePct ?? null,
    lastCheckIn: raw.lastCheckIn ?? null,
    nextFollowUp: raw.nextFollowUp ?? null,
    joinedAt: raw.joinedAt ?? raw.created_at ?? null,
  };
}

function computeAge(dateOfBirth) {
  const dob = new Date(dateOfBirth);
  if (Number.isNaN(dob.getTime())) return null;
  const diff = Date.now() - dob.getTime();
  return Math.floor(diff / (365.25 * 24 * 60 * 60 * 1000));
}

export async function createPatient(formData) {
  if (USE_MOCK) {
    await mockDelay(500);
    return createPatientRecord(formData);
  }
  const data = await apiFetch(ENDPOINTS.PATIENTS, {
    method: "POST",
    body: {
      full_name: formData.name || formData.full_name,
      date_of_birth: formData.date_of_birth || null,
      gender: (formData.gender || "other").toLowerCase(),
      phone_number: formData.phone || formData.phone_number || "",
      address: formData.address || "",
      medical_notes: formData.notes || formData.medical_notes || "",
      caretaker_name: formData.caretaker?.name || formData.caretaker_name || "",
      caretaker_relationship: formData.caretaker?.relationship || formData.caretaker_relationship || "",
      caretaker_phone_number: formData.caretaker?.phone || formData.caretaker_phone_number || "",
      caretaker_email: formData.caretaker?.email || formData.caretaker_email || "",
    },
  });
  return normalizePatient(data);
}

// Doctor's own patient list - was previously never fetched in live mode at
// all (DataContext seeded only from hardcoded demo data regardless of the
// USE_MOCK flag). See context/DataContext.jsx.
export async function getPatients() {
  if (USE_MOCK) {
    await mockDelay(200);
    return [];
  }
  const data = await apiFetch(ENDPOINTS.PATIENTS);
  const list = Array.isArray(data) ? data : data.results || [];
  return list.map(normalizePatient);
}

export async function getPatientDetail(id) {
  if (USE_MOCK) {
    await mockDelay(200);
    return null;
  }
  const data = await apiFetch(ENDPOINTS.PATIENT_BY_ID(id));
  return normalizePatient(data);
}

// The logged-in patient's own profile - GET /api/patients/me/. Used right
// after invitation redemption (Part 1 fix - see pages/patient/InvitationOnboarding.jsx)
// instead of fabricating a patient object from whatever the person just
// typed into the registration form.
export async function getMyPatientProfile() {
  if (USE_MOCK) {
    await mockDelay(200);
    return null;
  }
  const data = await apiFetch(ENDPOINTS.PATIENT_ME);
  return normalizePatient(data);
}

export { normalizePatient };
