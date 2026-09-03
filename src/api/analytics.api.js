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

export async function getPatientAISummary(patientId) {
  if (USE_MOCK) {
    await mockDelay(350);
    return {
      request_id: `mock_summary_${patientId}`,
      timestamp: new Date().toISOString(),
      history: {
        checkin_count: 3,
        days_since_last_checkin: 0,
        symptom_trend: {
          trend: "improving",
          observed_checkins: 3,
          latest_symptom_count: 1,
          previous_symptom_count: 2,
          detail: "Reported symptom count decreased from 2 to 1 across consecutive check-ins.",
        },
        vital_trend: {
          heart_rate: {
            latest_value: 74,
            previous_value: 78,
            delta: -4,
            trend: "decreasing",
          },
        },
        medications: [
          {
            id: 1,
            name: "Lisinopril",
            dosage: "10mg",
            frequency: "once_daily",
            start_date: "2026-08-01",
            end_date: null,
            is_active: true,
          },
        ],
        latest_lab: {
          id: 101,
          test_name: "HBA1C",
          status: "completed",
          result_text: "HbA1c 6.2%",
          result_date: "2026-08-28T10:00:00Z",
          reviewed: true,
        },
        open_follow_up: {
          id: 201,
          scheduled_at: "2026-09-10T14:30:00Z",
          status: "scheduled",
          reason: "Routine clinical follow-up",
        },
        medication_adherence: {
          overall_status: "adherent",
          medications: [
            {
              medication_id: 1,
              name: "Lisinopril",
              status: "adherent",
              reminders_sent: 7,
              reminders_acknowledged: 7,
              adherence_rate: 1.0,
            },
          ],
          detail: "Evaluated 1 medication(s). Overall adherence classified as adherent.",
        },
      },
    };
  }
  return apiFetch(ENDPOINTS.AI_SUMMARY_DOCTOR(patientId));
}

export async function getMyAISummary() {
  if (USE_MOCK) {
    await mockDelay(350);
    return {
      request_id: "mock_summary_me",
      timestamp: new Date().toISOString(),
      history: {
        checkin_count: 4,
        days_since_last_checkin: 0,
        symptom_trend: {
          trend: "stable",
          observed_checkins: 4,
          latest_symptom_count: 1,
          previous_symptom_count: 1,
          detail: "Reported symptom count is stable over recent check-ins.",
        },
        vital_trend: {},
        medications: [
          {
            id: 1,
            name: "Lisinopril",
            dosage: "10mg",
            frequency: "once_daily",
            start_date: "2026-08-01",
            end_date: null,
            is_active: true,
          },
        ],
        latest_lab: null,
        open_follow_up: {
          id: 201,
          scheduled_at: "2026-09-10T14:30:00Z",
          status: "scheduled",
          reason: "Routine clinical follow-up",
        },
        medication_adherence: {
          overall_status: "adherent",
          medications: [
            {
              medication_id: 1,
              name: "Lisinopril",
              status: "adherent",
              reminders_sent: 7,
              reminders_acknowledged: 7,
              adherence_rate: 1.0,
            },
          ],
          detail: "Overall adherence classified as adherent.",
        },
      },
    };
  }
  return apiFetch(ENDPOINTS.AI_SUMMARY_PATIENT);
}
