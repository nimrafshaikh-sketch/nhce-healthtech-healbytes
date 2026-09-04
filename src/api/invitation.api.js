import { apiFetch, USE_MOCK, mockDelay } from "./client";
import { ENDPOINTS } from "./endpoints";

export async function redeemInvitation({ code, email, username, password }, patients = []) {
  if (USE_MOCK) {
    await mockDelay(700);
    const normalized = String(code).trim().toUpperCase();
    // Root-cause fix (Part 1): never fall back to patients[0] when no code
    // matches - that's exactly how a fresh browser/device (with no prior
    // knowledge of a patient created elsewhere) used to silently redeem
    // into a random seeded demo patient instead of failing. Match strictly,
    // like the real backend's InvitationRedeemView does via the DB FK.
    const match = patients.find((p) => p.invitationCode?.toUpperCase() === normalized);
    if (!match) {
      const err = new Error("Invalid invitation code.");
      err.status = 400;
      throw err;
    }
    return {
      detail: "Account created and linked to doctor.",
      access: "mock-patient-access-token",
      refresh: "mock-patient-refresh-token",
      patient_id: match.id,
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
