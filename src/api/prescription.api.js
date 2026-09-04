import { apiFetch, USE_MOCK, mockDelay } from "./client";
import { initialPrescriptions } from "../data/demoData";
import { addMedication, getMedications } from "./medication.api";

let mockPrescriptions = [...initialPrescriptions];

export async function createPrescription({ patientId, medications = [] }) {
  if (USE_MOCK) {
    await mockDelay(800);
    const newPrescription = {
      id: `presc_${Date.now()}`,
      date: new Date().toISOString(),
      status: "ACTIVE",
      patientId,
      medications,
    };
    mockPrescriptions.unshift(newPrescription);
    return newPrescription;
  }

  const created = [];
  for (const med of medications) {
    const result = await addMedication(patientId, {
      name: med.name,
      dosage: med.dosage,
      frequency: med.frequency || "Once daily",
      instructions: med.instructions || "",
      timeOfDay: med.timeOfDay || "MORNING",
    });
    created.push(result);
  }
  return {
    id: created[0]?.id ?? null,
    date: new Date().toISOString(),
    status: "ACTIVE",
    patientId,
    medications: created,
  };
}

export async function getPrescriptionsForPatient(patientId) {
  if (USE_MOCK) {
    await mockDelay(400);
    return mockPrescriptions.filter((p) => p.patientId === patientId);
  }
  try {
    const raw = await apiFetch(`/medications/prescriptions/?patient=${patientId}`);
    const prescList = Array.isArray(raw) ? raw : (raw?.results || []);
    if (prescList.length > 0) {
      return prescList.map((p) => ({
        id: p.id,
        date: p.prescribed_at || p.created_at || new Date().toISOString(),
        status: p.status || "ACTIVE",
        medications: [
          {
            name: p.medication_name,
            dosage: p.dosage,
            frequency: p.frequency,
            duration: p.duration || "Ongoing",
            instructions: p.instructions || "Take as directed",
          }
        ]
      }));
    }
  } catch (e) {
    console.warn("Could not fetch /medications/prescriptions, falling back to /medications:", e);
  }

  // Fallback to active medications
  const meds = await getMedications(patientId);
  return (meds || []).map((m) => ({
    id: `med-${m.id}`,
    date: m.created_at || m.startDate || new Date().toISOString(),
    status: m.is_active ? "ACTIVE" : "INACTIVE",
    medications: [
      {
        name: m.name,
        dosage: m.dosage,
        frequency: m.frequency,
        duration: m.endDate ? `until ${m.endDate}` : "ongoing",
        instructions: m.instructions || "Take as directed",
      },
    ],
  }));
}
