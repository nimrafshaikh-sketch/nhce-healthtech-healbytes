import { apiFetch, USE_MOCK, mockDelay } from "./client";
import { ENDPOINTS } from "./endpoints";

// Mock-mode QR tokens are NOT real signed JWTs (there's no backend to verify
// them against) - but they must still round-trip through a real QR
// code image and a real camera decode, so they're plain strings carrying
// just enough to fake-resolve a patient locally. In live mode this is a
// genuine short-lived signed JWT from apps.qr.tokens.generate_qr_token,
// opaque to the frontend either way.
export async function generateQr(patientId) {
  if (USE_MOCK) {
    await mockDelay(300);
    const expires_at = new Date(Date.now() + 10 * 60 * 1000).toISOString();
    return { token: `mock-qr:${patientId}:${Date.now()}`, expires_at };
  }
  return apiFetch(ENDPOINTS.QR_GENERATE, { method: "POST", body: { patientId } });
}

export async function verifyQr(token, patients = [], { medications = [], checkins = [] } = {}) {
  if (USE_MOCK) {
    await mockDelay(500);
    const parts = String(token).split(":");
    const patientId = parts[0] === "mock-qr" ? parts[1] : null;
    const patient = patients.find((p) => p.id === patientId);
    if (!patient) {
      const err = new Error("Invalid or expired QR code.");
      err.status = 400;
      throw err;
    }
    return {
      patient,
      recent_medications: medications.filter((m) => m.patientId === patient.id),
      recent_checkins: checkins.filter((c) => c.patientId === patient.id),
      clinical_brief: null,
    };
  }
  return apiFetch(ENDPOINTS.QR_VERIFY, { method: "POST", body: { token } });
}
