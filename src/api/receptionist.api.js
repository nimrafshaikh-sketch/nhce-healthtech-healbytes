import { apiFetch, USE_MOCK, mockDelay } from "./client";

export async function searchPatients({ phone, name, dob }) {
  if (USE_MOCK) {
    await mockDelay(300);
    return [];
  }
  const params = new URLSearchParams();
  if (phone) params.set("phone_number", phone);
  if (name && dob) {
    params.set("name", name);
    params.set("date_of_birth", dob);
  }
  return apiFetch(`/patients/search/?${params.toString()}`);
}

export async function createReceptionistPatient(data) {
  if (USE_MOCK) {
    await mockDelay(400);
    return { id: 99, ...data };
  }
  return apiFetch("/patients/", {
    method: "POST",
    body: {
      doctor: Number(data.doctor),
      full_name: data.full_name,
      date_of_birth: data.date_of_birth,
      gender: (data.gender || "other").toLowerCase(),
      phone_number: data.phone_number,
      address: data.address || "",
      caretaker_name: data.caretaker_name || "",
      caretaker_relationship: data.caretaker_relationship || "",
      caretaker_phone_number: data.caretaker_phone_number || "",
      caretaker_email: data.caretaker_email || "",
    },
  });
}

export async function getDoctorsList() {
  if (USE_MOCK) {
    await mockDelay(200);
    return [{ id: 1, first_name: "Sarah", last_name: "Chen", email: "doctor@healbytes.local", specialization: "Internal Medicine" }];
  }
  return apiFetch("/auth/doctors/");
}

export async function getAppointments(patientId = null) {
  if (USE_MOCK) {
    await mockDelay(300);
    return [];
  }
  const url = patientId ? `/appointments/?patient=${patientId}` : "/appointments/";
  return apiFetch(url);
}

export async function bookAppointment({ patientId, doctorId, scheduledAt, reason, notes = "", durationMinutes = 30 }) {
  if (USE_MOCK) {
    await mockDelay(400);
    return { id: 101, patient: patientId, doctor: doctorId, scheduled_at: scheduledAt, reason, notes };
  }
  return apiFetch("/appointments/", {
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
}

export async function generatePatientInvitation(patientId) {
  if (USE_MOCK) {
    await mockDelay(400);
    return { code: "HB-7K29X", expires_at: null };
  }
  return apiFetch("/invitations/generate/", {
    method: "POST",
    body: { patient_id: Number(patientId) },
  });
}
