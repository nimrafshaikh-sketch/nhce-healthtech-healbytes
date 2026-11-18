import { USE_MOCK, mockDelay, currentToken, isJwtExpired, refreshAccessToken } from "./client.js";
import { analyzeCheckin } from "../services/riskEngine.js";

function readEnv() {
  return (typeof import.meta !== "undefined" && import.meta.env) || (typeof process !== "undefined" && process.env) || {};
}

export function getAiEngineBaseUrl() {
  const raw = readEnv().VITE_AI_ENGINE_URL || "http://localhost:8001";
  return String(raw).replace(/\/+$/, "");
}

export const AI_ENGINE_URL = getAiEngineBaseUrl();

export function formatAgentHttpError(status, detail, agentLabel) {
  if (status === 503) {
    return `${agentLabel} is currently offline (AI service not configured). Please try again later.`;
  }
  if (status === 502 || status === 504) {
    return `${agentLabel} could not reach the AI model provider. Please try again in a moment.`;
  }
  if (status === 401 || status === 403) {
    return `Your session expired or lacks permission for ${agentLabel}. Please sign in again.`;
  }
  if (detail && typeof detail === "string") {
    return detail;
  }
  return `${agentLabel} request failed (${status}).`;
}

async function requestAgent(path, buildBody, agentLabel, _retried = false) {
  let token = currentToken();

  if (!USE_MOCK && token && isJwtExpired(token)) {
    const renewed = await refreshAccessToken();
    if (renewed) {
      token = renewed;
    }
  }

  let res;
  try {
    res = await fetch(`${getAiEngineBaseUrl()}${path}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(buildBody(token)),
    });
  } catch {
    const networkErr = new Error(
      `${agentLabel} is currently offline or unreachable. Please verify the AI Engine service is running and try again.`
    );
    networkErr.status = 0;
    networkErr.code = "NETWORK_ERROR";
    throw networkErr;
  }

  if (res.status === 401 && !USE_MOCK && !_retried) {
    const renewed = await refreshAccessToken();
    if (renewed) {
      return requestAgent(path, buildBody, agentLabel, true);
    }
  }

  if (!res.ok) {
    const errBody = await res.json().catch(() => ({}));
    const err = new Error(formatAgentHttpError(res.status, errBody.detail, agentLabel));
    err.status = res.status;
    err.data = errBody;
    throw err;
  }

  return res.json();
}

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
  return requestAgent(
    "/api/v1/agents/doctor",
    (token) => ({
      request_id: `doc-${Date.now()}`,
      patient_id: String(patientId),
      message,
      conversation_history: conversationHistory,
      auth_token: token,
    }),
    "AI Clinical Copilot"
  );
}

/**
 * Sends a natural-language front-desk request to the Gemini Receptionist Agent.
 * Automatically injects the active receptionist's auth token and request ID.
 */
export async function queryReceptionistAgent({ message, patientId = null, conversationHistory = [] }) {
  return requestAgent(
    "/api/v1/agents/receptionist",
    (token) => ({
      request_id: `rec-${Date.now()}`,
      patient_id: patientId ? String(patientId) : null,
      message,
      conversation_history: conversationHistory,
      auth_token: token,
    }),
    "Front-Desk AI Assistant"
  );
}

