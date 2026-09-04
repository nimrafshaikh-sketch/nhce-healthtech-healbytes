import { USE_MOCK, mockDelay, currentToken } from "./client";
import { analyzeCheckin } from "../services/riskEngine";

// Mock-mode-only: simulates the AI engine's turnaround time and returns a
// locally-computed risk verdict. In live mode, the AI verdict for a check-in
// does not come back synchronously from a dedicated "analyze" endpoint - the
// real Django backend queues the AI analysis (apps.checkins.tasks) after the
// check-in is saved via POST /checkins/, then stores the result back onto
// that same checkin record. See api/checkin.api.js::waitForCheckinResult,
// which is what context/DataContext.jsx actually calls in live mode.
export async function analyzeCheckinAI(payload) {
  if (!USE_MOCK) {
    throw new Error("analyzeCheckinAI is mock-mode only; use waitForCheckinResult in live mode.");
  }
  await mockDelay(1800);
  return analyzeCheckin(payload);
}

/**
 * Sends a natural-language clinical question to the Gemini Doctor Agent.
 * Automatically injects the active doctor's auth token, patient ID, and request ID.
 */
export async function queryDoctorAgent({ patientId, message, conversationHistory = [] }) {
  const token = currentToken();
  const res = await fetch("http://localhost:8001/api/v1/agents/doctor", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({
      request_id: `doc-${Date.now()}`,
      patient_id: String(patientId),
      message,
      conversation_history: conversationHistory,
      auth_token: token,
    }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Doctor Agent request failed (${res.status})`);
  }
  return res.json();
}

/**
 * Sends a natural-language front-desk request to the Gemini Receptionist Agent.
 * Automatically injects the active receptionist's auth token and request ID.
 */
export async function queryReceptionistAgent({ message, patientId = null, conversationHistory = [] }) {
  const token = currentToken();
  const res = await fetch("http://localhost:8001/api/v1/agents/receptionist", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({
      request_id: `rec-${Date.now()}`,
      patient_id: patientId ? String(patientId) : null,
      message,
      conversation_history: conversationHistory,
      auth_token: token,
    }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Receptionist Agent request failed (${res.status})`);
  }
  return res.json();
}

