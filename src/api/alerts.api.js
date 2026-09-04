import { apiFetch, USE_MOCK, mockDelay } from "./client";
import { ENDPOINTS } from "./endpoints";
import { getInitials } from "../services/mockService";

// GET /alerts/ (doctor-only, own patients) was defined in ENDPOINTS but
// never actually called from anywhere in the frontend - "Recent AI
// Insights" on the doctor dashboard and the whole doctor/patient Alerts
// pages only ever showed whatever was seeded into demoData or generated
// client-side during the current browser session (see context/DataContext.jsx
// submitCheckin), even against a real backend. This is the real fetch.
// Backend severity/status are lowercase and 3-state (open/acknowledged/
// resolved); the UI only distinguishes ACTIVE vs RESOLVED - both
// open+acknowledged map to ACTIVE. There's no numeric risk score on Alert
// itself (that lives on the originating DailyCheckin, not copied over), so
// riskScore is left null here rather than fabricated.
function normalizeAlert(raw) {
  const severityMap = { low: "LOW", medium: "MEDIUM", high: "HIGH" };
  return {
    id: raw.id,
    patientId: raw.patient,
    patientName: raw.patient_name || "Patient",
    avatarInitials: getInitials(raw.patient_name || ""),
    riskLevel: severityMap[raw.severity] || "LOW",
    riskScore: null,
    message: raw.reason || "",
    detectedAt: raw.created_at,
    status: raw.status === "resolved" ? "RESOLVED" : "ACTIVE",
  };
}

export async function getAlerts() {
  if (USE_MOCK) {
    await mockDelay(200);
    return null; // caller keeps whatever's already in state (demo seed data)
  }
  const data = await apiFetch(ENDPOINTS.ALERTS);
  const list = Array.isArray(data) ? data : data.results || [];
  return list.map(normalizeAlert);
}

export async function resolveAlert(alertId) {
  if (USE_MOCK) {
    await mockDelay(300);
    return { id: alertId, status: "RESOLVED" };
  }
  // Was PUT - the backend view (AlertResolveView) only implements POST, so
  // this 405'd against the real backend every time.
  return apiFetch(ENDPOINTS.ALERT_RESOLVE(alertId), { method: "POST" });
}
