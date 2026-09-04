import { USE_MOCK, mockDelay } from "./client";
import { initialPrescriptions } from "../data/demoData";
import { addMedication, getMedications } from "./medication.api";

// There is no separate "Prescription" resource in the Django backend - a
// digital prescription IS one or more apps.medications.Medication rows
// (apps/patients/serializers.py has no prescription concept either). The
// previous live-mode implementation here POSTed to `/prescriptions` and
// GETed `/patients/:id/prescriptions`, neither of which exist server-side -
// every live call 404'd silently (caught by the modal's generic
// "Failed to create prescription" alert, so it looked like a validation
// error rather than a wrong endpoint). Root-cause fix: route through the
// real Medication endpoints, one Medication per line item, and adapt the
// response back into the {id, date, medications: [...]} shape the existing
// "Prescriptions" tab UI already renders - no UI changes needed, and no
// second parallel prescription system introduced.
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
  // Real backend has no prescription "batch" grouping - render one card per
  // Medication, each wrapped as a single-item "prescription" so the
  // existing UI (which maps over `.medications`) needs no changes.
  const meds = await getMedications(patientId);
  return meds.map((m) => ({
    id: `med-${m.id}`,
    date: m.created_at || m.startDate,
    status: m.is_active ? "ACTIVE" : "INACTIVE",
    medications: [
      {
        name: m.name,
        dosage: m.dosage,
        frequency: m.frequency,
        duration: m.endDate ? `until ${m.endDate}` : "ongoing",
        instructions: m.instructions,
      },
    ],
  }));
}
