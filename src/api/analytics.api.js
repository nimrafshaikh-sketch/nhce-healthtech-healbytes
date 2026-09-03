import { apiFetch, USE_MOCK, mockDelay } from "./client";
import { ENDPOINTS } from "./endpoints";

export async function getDoctorAnalytics(patients = []) {
  if (USE_MOCK) {
    await mockDelay(300);
    const total = patients.length;
    const low = patients.filter((p) => p.riskLevel === "LOW").length;
    const medium = patients.filter((p) => p.riskLevel === "MEDIUM").length;
    const high = patients.filter((p) => p.riskLevel === "HIGH").length;
    const avgAdherence = total
      ? Math.round(patients.reduce((sum, p) => sum + (p.medicationAdherencePct || 0), 0) / total)
      : 0;
    return { total, low, medium, high, avgAdherence };
  }
  return apiFetch(ENDPOINTS.ANALYTICS_DOCTOR);
}
