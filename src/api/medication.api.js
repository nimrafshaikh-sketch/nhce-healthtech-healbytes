import { apiFetch, USE_MOCK, mockDelay } from "./client";
import { ENDPOINTS } from "./endpoints";
import { generateId } from "../utils/id";

export async function addMedication(patientId, formData) {
  if (USE_MOCK) {
    await mockDelay(400);
    return { id: generateId("med"), patientId, status: "PENDING", ...formData };
  }
  return apiFetch(ENDPOINTS.MEDICATIONS_BY_PATIENT(patientId), { method: "POST", body: formData });
}

export async function markMedicationStatus(medicationId, status) {
  if (USE_MOCK) {
    await mockDelay(250);
    return { id: medicationId, status, takenAt: status === "TAKEN" ? new Date() : null };
  }
  return apiFetch(ENDPOINTS.MEDICATION_TAKEN(medicationId), { method: "POST", body: { status } });
}
