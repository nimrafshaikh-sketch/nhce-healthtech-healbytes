import { apiFetch, USE_MOCK, mockDelay } from "./client";
import { ENDPOINTS } from "./endpoints";
import { createPatientRecord } from "../services/mockService";

export async function createPatient(formData) {
  if (USE_MOCK) {
    await mockDelay(500);
    return createPatientRecord(formData);
  }
  return apiFetch(ENDPOINTS.PATIENTS, { method: "POST", body: formData });
}
