import { apiFetch, USE_MOCK, mockDelay } from "./client";
import { initialPrescriptions } from "../data/demoData";

let mockPrescriptions = [...initialPrescriptions];

export async function createPrescription(data) {
  if (USE_MOCK) {
    await mockDelay(800);
    const newPrescription = {
      id: `presc_${Date.now()}`,
      date: new Date().toISOString(),
      status: "ACTIVE",
      ...data,
    };
    mockPrescriptions.unshift(newPrescription);
    return newPrescription;
  }
  return apiFetch(`/prescriptions`, { method: "POST", body: data });
}

export async function getPrescriptionsForPatient(patientId) {
  if (USE_MOCK) {
    await mockDelay(400);
    return mockPrescriptions.filter((p) => p.patientId === patientId);
  }
  return apiFetch(`/patients/${patientId}/prescriptions`);
}

// Simulated OCR placeholder
export async function uploadPrescriptionImage(file) {
  if (USE_MOCK) {
    await mockDelay(2000); // Simulate processing time
    // Mock OCR result
    return {
      success: true,
      extractedData: {
        medications: [
          {
            name: "Amoxicillin",
            dosage: "500 mg",
            frequency: "Twice daily",
            duration: "5 days",
            instructions: "After food",
          },
        ],
      },
    };
  }
  const formData = new FormData();
  formData.append("file", file);
  return apiFetch(`/prescriptions/upload`, { method: "POST", body: formData });
}
