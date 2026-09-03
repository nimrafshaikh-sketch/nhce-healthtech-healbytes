import { apiFetch, USE_MOCK, mockDelay } from "./client";
import { initialAppointments } from "../data/demoData";

let mockAppointments = [...initialAppointments];

export async function getAvailableSlots(doctorId, dateStr) {
  if (USE_MOCK) {
    await mockDelay(500);
    return ["09:00 AM", "10:30 AM", "02:00 PM", "04:15 PM"];
  }
  return apiFetch(`/appointments/slots?doctorId=${doctorId}&date=${dateStr}`);
}

export async function confirmAppointment(data) {
  if (USE_MOCK) {
    await mockDelay(700);
    const appt = {
      id: `appt_${Date.now()}`,
      status: "CONFIRMED",
      ...data,
    };
    mockAppointments.unshift(appt);
    return appt;
  }
  return apiFetch(`/appointments`, { method: "POST", body: data });
}

export async function getAppointmentsForPatient(patientId) {
  if (USE_MOCK) {
    await mockDelay(400);
    return mockAppointments.filter((a) => a.patientId === patientId);
  }
  return apiFetch(`/patients/${patientId}/appointments`);
}
