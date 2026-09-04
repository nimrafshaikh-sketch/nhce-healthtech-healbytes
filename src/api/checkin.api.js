import { apiFetch, USE_MOCK, mockDelay } from "./client";
import { ENDPOINTS } from "./endpoints";
import { generateId } from "../utils/id";

export async function submitCheckin(payload) {
  if (USE_MOCK) {
    await mockDelay(300);
    return { id: generateId("chk"), date: new Date(), ...payload };
  }
  return apiFetch(ENDPOINTS.CHECKINS, { method: "POST", body: payload });
}

export async function getCheckin(id) {
  return apiFetch(ENDPOINTS.CHECKIN_BY_ID(id));
}

// Django's create-checkin response never includes the AI verdict - the risk
// analysis runs afterward via a Celery task (backend apps.checkins.tasks)
// that writes ai_risk_level/ai_risk_score/... back onto the same row. This
// maps those fields into the shape the UI already expects (uppercase
// LOW/MEDIUM/HIGH, 0-100 score) rather than the raw lowercase/0.0-1.0 the
// backend stores.
function normalizeAiFields(raw) {
  const levelMap = { low: "LOW", medium: "MEDIUM", high: "HIGH" };
  return {
    ready: Boolean(raw.ai_processed_at),
    riskLevel: levelMap[raw.ai_risk_level] || null,
    riskScore: typeof raw.ai_risk_score === "number" ? Math.round(raw.ai_risk_score * 100) : null,
    reason: raw.ai_notes || "",
    followUpAction: raw.ai_recommended_action || "",
    recommendation: raw.ai_recommended_action || "",
  };
}

// Polls the checkin detail endpoint for the AI verdict right after
// submission. Locally (CELERY_TASK_ALWAYS_EAGER=True, see backend
// config/settings/dev.py) the task has already run by the time the create
// request returns, so this normally resolves on the very first GET; against
// a real async worker it waits a little longer. If the AI engine is slow or
// unreachable, falls back to a "still processing" result instead of hanging
// the check-in flow forever - the real verdict will show up next time the
// patient's data is refreshed (ai_risk_level flips off "pending").
export async function waitForCheckinResult(id, { attempts = 6, delayMs = 700 } = {}) {
  for (let i = 0; i < attempts; i++) {
    const raw = await getCheckin(id);
    const result = normalizeAiFields(raw);
    if (result.ready) return result;
    if (i < attempts - 1) await mockDelay(delayMs);
  }
  return {
    ready: false,
    riskLevel: "LOW",
    riskScore: null,
    reason: "Your care team will review this check-in shortly.",
    followUpAction: "",
    recommendation: "Your care team will review this check-in shortly.",
  };
}
