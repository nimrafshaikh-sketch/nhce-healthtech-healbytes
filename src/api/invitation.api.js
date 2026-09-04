import { apiFetch, USE_MOCK, mockDelay } from "./client";
import { ENDPOINTS } from "./endpoints";

export async function redeemInvitation({ code, email, username, password }, patients = []) {
  if (USE_MOCK) {
    await mockDelay(700);
    const normalized = String(code).trim().toUpperCase();
    const match = patients.find((p) => p.invitationCode?.toUpperCase() === normalized) || patients[0];
    return {
      detail: "Account created and linked to doctor.",
      access: "mock-patient-access-token",
      refresh: "mock-patient-refresh-token",
      patient_id: match?.id || 1,
      patient: match,
    };
  }
  return apiFetch(ENDPOINTS.INVITATIONS_VERIFY, {
    method: "POST",
    body: {
      code: String(code).trim().toUpperCase(),
      email: String(email).trim(),
      username: String(username).trim(),
      password: String(password),
    },
  });
}

export async function generateInvitation(patientId, patients = []) {
  if (USE_MOCK) {
    await mockDelay(400);
    const patient = patients.find((p) => p.id === patientId);
    return { code: patient?.invitationCode || "HB-7K29X", expiresAt: null };
  }
  return apiFetch(ENDPOINTS.INVITATIONS, {
    method: "POST",
    body: { patient_id: Number(patientId) },
  });
}
