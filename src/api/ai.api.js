import { apiFetch, USE_MOCK, mockDelay } from "./client";
import { ENDPOINTS } from "./endpoints";
import { analyzeCheckin } from "../services/riskEngine";

// This is the one function to repoint at the real AI service later —
// everything upstream (the check-in flow, the result screen) is unaffected.
export async function analyzeCheckinAI(payload) {
  if (USE_MOCK) {
    await mockDelay(1800);
    return analyzeCheckin(payload);
  }
  return apiFetch(ENDPOINTS.AI_ANALYZE_CHECKIN, { method: "POST", body: payload });
}
