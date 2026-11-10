import { apiFetch, USE_MOCK, mockDelay } from "./client.js";
import { ENDPOINTS } from "./endpoints.js";
import { generateId } from "../utils/id.js";

const SEVERITY_PAIN_MAP = { MILD: 2, MODERATE: 5, SEVERE: 8 };
const RISK_LEVEL_MAP = {
  low: "LOW",
  medium: "MEDIUM",
  high: "HIGH",
  pending: "PENDING",
  unavailable: "UNAVAILABLE",
};

export function localDateString(date = new Date()) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

export function derivePainLevel(symptoms = []) {
  if (!Array.isArray(symptoms) || symptoms.length === 0) return null;
  let maxPain = null;
  for (const s of symptoms) {
    if (s && typeof s === "object") {
      const sev = String(s.severity || "").toUpperCase();
      const score = SEVERITY_PAIN_MAP[sev];
      if (score != null) {
        maxPain = maxPain == null ? score : Math.max(maxPain, score);
      }
    }
  }
  return maxPain;
}

function normalizeSymptoms(rawSymptoms) {
  if (!Array.isArray(rawSymptoms)) return [];
  return rawSymptoms
    .map((s) => {
      if (typeof s === "string") return { name: s, severity: null };
      if (s && typeof s === "object") {
        return {
          name: s.name || s.symptom || s.title || "Symptom",
          severity: s.severity ? String(s.severity).toUpperCase() : null,
        };
      }
      return null;
    })
    .filter(Boolean);
}

// Django's create-checkin response initializes ai_risk_level="pending" while
// Celery runs process_checkin_ai_analysis -> analyze_checkin -> route_alert_for_checkin.
export function normalizeAiFields(raw) {
  const rawLevel = String(raw?.ai_risk_level || "").toLowerCase();
  const riskLevel = RISK_LEVEL_MAP[rawLevel] || "UNAVAILABLE";
  return {
    ready: Boolean(raw?.ai_processed_at) || (rawLevel !== "" && rawLevel !== "pending"),
    riskLevel,
    riskScore: typeof raw?.ai_risk_score === "number" ? Math.round(raw.ai_risk_score * 100) : null,
    reason: raw?.ai_notes || "",
    followUpAction: raw?.ai_recommended_action || "",
    recommendation: raw?.ai_recommended_action || "",
    notificationRecipient: raw?.ai_notification_recipient || "",
  };
}

export function normalizeCheckin(raw) {
  if (!raw) return null;
  const ai = normalizeAiFields(raw);
  const createdAt = raw.created_at || null;
  const checkinDate = raw.checkin_date || null;
  return {
    id: raw.id,
    patientId: raw.patient ?? raw.patientId,
    patientName: raw.patient_name || "",
    date: createdAt || checkinDate || new Date().toISOString(),
    checkinDate,
    createdAt,
    symptoms: normalizeSymptoms(raw.symptoms),
    overallFeeling: raw.mood ? String(raw.mood).toUpperCase() : raw.overallFeeling || null,
    painLevel: raw.pain_level ?? raw.painLevel ?? null,
    duration: raw.symptom_duration || raw.duration || null,
    medicationAdherence: raw.medication_adherence || raw.medicationAdherence || null,
    notes: raw.notes || "",
    vitals: raw.vitals || {},
    ...ai,
  };
}

export async function submitCheckin(payload) {
  if (USE_MOCK) {
    await mockDelay(300);
    return { id: generateId("chk"), date: new Date(), ...payload };
  }
  const symptoms = Array.isArray(payload.symptoms) ? payload.symptoms : [];
  const body = {
    checkin_date: payload.checkinDate || payload.checkin_date || localDateString(),
    symptoms,
    mood: payload.overallFeeling ? String(payload.overallFeeling).toLowerCase() : "",
    pain_level: payload.painLevel ?? payload.pain_level ?? derivePainLevel(symptoms),
    duration: payload.duration || "",
    symptom_duration: payload.duration || payload.symptom_duration || "",
    medication_adherence: payload.medicationAdherence || payload.medication_adherence || "",
    notes: payload.notes || "",
  };
  const created = await apiFetch(ENDPOINTS.CHECKINS, { method: "POST", body });
  return normalizeCheckin(created);
}

export async function getCheckins(patientId = null) {
  if (USE_MOCK) {
    await mockDelay(200);
    return null;
  }
  const url = patientId ? ENDPOINTS.CHECKINS_BY_PATIENT(patientId) : ENDPOINTS.CHECKINS;
  const data = await apiFetch(url);
  const list = Array.isArray(data) ? data : data.results || [];
  return list.map(normalizeCheckin);
}

export async function getCheckin(id) {
  return apiFetch(ENDPOINTS.CHECKIN_BY_ID(id));
}

export async function waitForCheckinResult(id, { attempts = 6, delayMs = 700 } = {}) {
  for (let i = 0; i < attempts; i++) {
    const raw = await getCheckin(id);
    const result = normalizeAiFields(raw);
    if (result.ready) return result;
    if (i < attempts - 1) await mockDelay(delayMs);
  }
  return {
    ready: false,
    riskLevel: "PENDING",
    riskScore: null,
    reason: "Your check-in has been saved and queued for automated risk review.",
    followUpAction: "",
    recommendation: "",
  };
}
