import { USE_MOCK, mockDelay } from "./client";
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
