import { apiFetch, USE_MOCK, mockDelay } from "./client";
import { initialPatients } from "../data/demoData";

// Temporary in-memory state for mock updates
let mockPatients = [...initialPatients];

export async function searchPatient(query) {
  if (USE_MOCK) {
    await mockDelay(500);
    if (!query) return [];
    const q = query.toLowerCase();
    return mockPatients.filter(
      (p) =>
        p.name.toLowerCase().includes(q) ||
        p.phone.includes(q) ||
        p.id.toLowerCase().includes(q)
    );
  }
  return apiFetch(`/reception/patients?q=${encodeURIComponent(query)}`);
}

export async function createPatient(patientData) {
  if (USE_MOCK) {
    await mockDelay(800);
    const newPatient = {
      id: `pat_new_${Date.now()}`,
      role: "PATIENT",
      riskLevel: "LOW", // default
      riskScore: 0,
      medicationAdherencePct: 100,
      ...patientData,
      avatarInitials: patientData.name
        .split(" ")
        .map((n) => n[0])
        .join("")
        .toUpperCase()
        .substring(0, 2),
    };
    mockPatients.push(newPatient);
    return newPatient;
  }
  return apiFetch(`/reception/patients`, { method: "POST", body: patientData });
}

export async function getPatientById(id) {
  if (USE_MOCK) {
    await mockDelay(300);
    const p = mockPatients.find((pat) => pat.id === id);
    if (!p) throw new Error("Patient not found");
    return p;
  }
  return apiFetch(`/patients/${id}`);
}
