import { apiFetch, USE_MOCK, mockDelay } from "./client";
import { ENDPOINTS } from "./endpoints";
import { generateId } from "../utils/id";

const FREQUENCY_MAP = {
  "Once daily": "once_daily",
  "Twice daily": "twice_daily",
  "Three times daily": "three_times_daily",
  "Weekly": "weekly",
  "As needed": "as_needed",
  once_daily: "once_daily",
  twice_daily: "twice_daily",
  three_times_daily: "three_times_daily",
  weekly: "weekly",
  as_needed: "as_needed",
};

const TIME_MAP = {
  MORNING: ["08:00"],
  AFTERNOON: ["13:00"],
  EVENING: ["20:00"],
};

export async function addMedication(patientId, formData) {
  if (USE_MOCK) {
    await mockDelay(400);
    return { id: generateId("med"), patientId, status: "PENDING", ...formData };
  }

  const frequency = FREQUENCY_MAP[formData.frequency] || "once_daily";
  const reminder_times = TIME_MAP[formData.timeOfDay] || ["08:00"];

  const payload = {
    patient: Number(patientId),
    name: formData.name,
    dosage: formData.dosage,
    frequency,
    instructions: formData.instructions || "",
    start_date: formData.startDate || new Date().toISOString().split("T")[0],
    end_date: formData.endDate || null,
    reminder_times,
    reminders_enabled: true,
    is_active: true,
  };

  const data = await apiFetch(ENDPOINTS.MEDICATIONS, { method: "POST", body: payload });
  return {
    ...data,
    patientId: data.patient,
    startDate: data.start_date,
    endDate: data.end_date,
    timeOfDay: formData.timeOfDay || "MORNING",
    status: data.is_active ? "ACTIVE" : "INACTIVE",
  };
}

export async function getMedications(patientId) {
  if (USE_MOCK) {
    await mockDelay(200);
    return [];
  }
  const endpoint = patientId ? ENDPOINTS.MEDICATIONS_BY_PATIENT(patientId) : ENDPOINTS.MEDICATIONS;
  const data = await apiFetch(endpoint);
  const list = Array.isArray(data) ? data : data.results || [];
  return list.map((m) => {
    let tod = "MORNING";
    const rt = m.reminder_times?.[0] || "";
    if (rt.startsWith("13") || rt.startsWith("14") || rt.startsWith("12")) tod = "AFTERNOON";
    else if (rt.startsWith("18") || rt.startsWith("19") || rt.startsWith("20") || rt.startsWith("21")) tod = "EVENING";
    return {
      ...m,
      patientId: m.patient,
      startDate: m.start_date,
      endDate: m.end_date,
      timeOfDay: tod,
      status: m.is_active ? "ACTIVE" : "INACTIVE",
    };
  });
}

export async function markMedicationStatus(medicationId, status) {
  if (USE_MOCK) {
    await mockDelay(250);
    return { id: medicationId, status, takenAt: status === "TAKEN" ? new Date() : null };
  }
  return { id: medicationId, status, takenAt: status === "TAKEN" ? new Date() : null };
}

