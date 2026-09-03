import { apiFetch, USE_MOCK, mockDelay } from "./client";
import { ENDPOINTS } from "./endpoints";

export async function generateQr(patientId) {
  if (USE_MOCK) {
    await mockDelay(300);
    return { token: `qr_${patientId}_${Date.now()}`, updatedAt: new Date() };
  }
  return apiFetch(ENDPOINTS.QR_GENERATE, { method: "POST", body: { patientId } });
}

export async function verifyQr(token, patients = []) {
  if (USE_MOCK) {
    await mockDelay(500);
    const patientId = token?.split("_")[1];
    const patient = patients.find((p) => p.id === patientId) || patients[0];
    return { patient };
  }
  return apiFetch(ENDPOINTS.QR_VERIFY, { method: "POST", body: { token } });
}
