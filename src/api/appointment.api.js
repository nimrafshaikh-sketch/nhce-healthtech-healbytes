import { apiFetch, USE_MOCK, mockDelay } from "./client";
import { ENDPOINTS } from "./endpoints";
import { initialAppointments } from "../data/demoData";

// Patient-facing appointments API. This module previously called endpoints
// that don't exist anywhere in the Django backend (`/appointments/slots`,
// `POST /appointments` with no trailing slash, `/patients/:id/appointments`)
// and its one consumer, components/patient/AppointmentFollowUp.jsx, was
// itself never imported by any page - so none of this ever ran against the
// real backend. Rewritten to match the actual, already-working contract
// used by src/api/receptionist.api.js (GET/POST /appointments/,
// POST /appointments/:id/confirm/, POST /appointments/:id/cancel/) and
// wired up for real in pages/patient/Appointments.jsx.

let mockAppointments = [...initialAppointments];

// Mock demo data and the live Django serializer use different shapes
// (doctorName/date/time vs doctor_name/scheduled_at, uppercase vs lowercase
// status) - this normalizes either into one shape the UI can render.
function normalizeAppointment(raw) {
  const scheduledAt = raw.scheduled_at
    ? new Date(raw.scheduled_at)
    : raw.date
    ? new Date(raw.date)
    : null;
  return {
    id: raw.id,
    patientId: raw.patient ?? raw.patient_id ?? raw.patientId ?? null,
    patient: raw.patient ?? raw.patient_id ?? raw.patientId ?? null,
    patientName: raw.patient_name || raw.patientName || raw.patient_fullName || "Patient",
    doctorId: raw.doctor ?? raw.doctor_id ?? raw.doctorId ?? null,
    doctor: raw.doctor ?? raw.doctor_id ?? raw.doctorId ?? null,
    doctorName: raw.doctor_name || raw.doctorName || "",
    reason: raw.reason || "Consultation",
    status: (raw.status || "SCHEDULED").toUpperCase(),
    scheduledAt,
    timeLabel: raw.time || null,
    durationMinutes: raw.duration_minutes || raw.durationMinutes || 30,
    notes: raw.notes || "",
  };
}

export async function getMyAppointments() {
  if (USE_MOCK) {
    await mockDelay(300);
    return mockAppointments.map(normalizeAppointment);
  }
  const data = await apiFetch(ENDPOINTS.APPOINTMENTS);
  const list = Array.isArray(data) ? data : data.results || [];
  return list.map(normalizeAppointment);
}

// Used by the doctor's "Schedule Follow-up" action (pages/doctor/
// PatientProfile.jsx). Previously that action only did a local
// DataContext.updatePatient({ nextFollowUp: {...} }) dispatch - no API call
// at all - so the "appointment" it created was invisible to the backend
// Appointment model, and therefore invisible to the receptionist dashboard
// and to the patient's own appointments list. This creates a real one.
export async function createAppointment({ patientId, doctorId, scheduledAt, reason, notes = "", durationMinutes = 30 }) {
  if (USE_MOCK) {
    await mockDelay(400);
    const appt = {
      id: `appt_${Date.now()}`,
      patient: patientId,
      doctor: doctorId,
      scheduled_at: scheduledAt,
      reason,
      notes,
      status: "SCHEDULED",
    };
    mockAppointments = [appt, ...mockAppointments];
    return normalizeAppointment(appt);
  }
  const data = await apiFetch(ENDPOINTS.APPOINTMENTS, {
    method: "POST",
    body: {
      patient: Number(patientId),
      doctor: Number(doctorId),
      scheduled_at: scheduledAt,
      duration_minutes: Number(durationMinutes),
      reason,
      notes,
    },
  });
  return normalizeAppointment(data);
}

export async function confirmAppointment(id) {
  if (USE_MOCK) {
    await mockDelay(300);
    const appt = mockAppointments.find((a) => a.id === id);
    if (appt) appt.status = "CONFIRMED";
    return normalizeAppointment(appt);
  }
  const data = await apiFetch(ENDPOINTS.APPOINTMENT_CONFIRM(id), { method: "POST" });
  return normalizeAppointment(data);
}

export async function cancelAppointment(id) {
  if (USE_MOCK) {
    await mockDelay(300);
    const appt = mockAppointments.find((a) => a.id === id);
    if (appt) appt.status = "CANCELLED";
    return normalizeAppointment(appt);
  }
  const data = await apiFetch(ENDPOINTS.APPOINTMENT_CANCEL(id), { method: "POST" });
  return normalizeAppointment(data);
}
