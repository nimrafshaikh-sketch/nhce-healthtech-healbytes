import { apiFetch, USE_MOCK, mockDelay } from "./client";
import { ENDPOINTS } from "./endpoints";

export async function verifyInvitation(code, patients = []) {
  if (USE_MOCK) {
    await mockDelay(700);
    const normalized = String(code).trim().toUpperCase();
    const match = patients.find((p) => p.invitationCode?.toUpperCase() === normalized);
    if (!match) {
      throw new Error("We couldn't find that invitation code. Double-check with your doctor and try again.");
    }
    return { patient: match };
  }
  return apiFetch(ENDPOINTS.INVITATIONS_VERIFY, { method: "POST", body: { code } });
}

export async function generateInvitation(patientId, patients = []) {
  if (USE_MOCK) {
    await mockDelay(400);
    const patient = patients.find((p) => p.id === patientId);
    return { code: patient?.invitationCode, expiresAt: null };
  }
  return apiFetch(ENDPOINTS.INVITATIONS, { method: "POST", body: { patientId } });
}
