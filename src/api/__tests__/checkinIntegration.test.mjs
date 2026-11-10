import test from "node:test";
import assert from "node:assert/strict";

const store = new Map();
globalThis.localStorage = {
  getItem: (k) => (store.has(k) ? store.get(k) : null),
  setItem: (k, v) => store.set(k, String(v)),
  removeItem: (k) => store.delete(k),
  clear: () => store.clear(),
};
globalThis.window = {
  dispatchEvent: () => {},
  addEventListener: () => {},
  removeEventListener: () => {},
};
globalThis.Event = class Event {
  constructor(type) {
    this.type = type;
  }
};

import { setStoredAuth } from "../client.js";
import {
  derivePainLevel,
  getCheckins,
  localDateString,
  normalizeAiFields,
  normalizeCheckin,
  submitCheckin,
  waitForCheckinResult,
} from "../checkin.api.js";
import { getAlerts } from "../alerts.api.js";
import { normalizePatient } from "../patients.api.js";
import {
  formatDateTime,
  formatDayLabel,
  formatTime,
  isDateOnlyString,
  isSameLocalDay,
  parseDateInput,
} from "../../utils/dateUtils.js";

function makeLiveToken(role = "patient", userId = 10) {
  const nowSec = Math.floor(Date.now() / 1000);
  const header = Buffer.from(JSON.stringify({ alg: "HS256", typ: "JWT" })).toString("base64url");
  const payload = Buffer.from(JSON.stringify({ user_id: userId, role, exp: nowSec + 3600 })).toString("base64url");
  return `${header}.${payload}.sig`;
}

test("dateUtils handles YYYY-MM-DD in local calendar without empty/UTC shift", () => {
  assert.equal(isDateOnlyString("2026-11-10"), true);
  assert.equal(isDateOnlyString("2026-11-10T09:30:00Z"), false);

  const parsed = parseDateInput("2026-11-10");
  assert.ok(parsed instanceof Date);
  assert.equal(parsed.getFullYear(), 2026);
  assert.equal(parsed.getMonth(), 10);
  assert.equal(parsed.getDate(), 10);

  assert.equal(formatTime("2026-11-10"), "");
  assert.equal(isSameLocalDay(localDateString(new Date()), new Date()), true);
  assert.equal(formatDayLabel(localDateString(new Date())), "Today");
  assert.equal(formatDateTime(null), "—");
});

test("derivePainLevel picks maximum severity across multiple symptoms", () => {
  assert.equal(derivePainLevel([]), null);
  assert.equal(derivePainLevel([{ name: "Fatigue", severity: "MILD" }]), 2);
  assert.equal(
    derivePainLevel([
      { name: "Fatigue", severity: "MILD" },
      { name: "Chest Pain", severity: "SEVERE" },
      { name: "Dizziness", severity: "MODERATE" },
    ]),
    8
  );
});

test("normalizeAiFields represents pending/unavailable honestly instead of LOW", () => {
  const pending = normalizeAiFields({ ai_risk_level: "pending", ai_risk_score: null });
  assert.equal(pending.ready, false);
  assert.equal(pending.riskLevel, "PENDING");
  assert.equal(pending.riskScore, null);

  const unavailable = normalizeAiFields({ ai_risk_level: "unavailable", ai_risk_score: null });
  assert.equal(unavailable.ready, true);
  assert.equal(unavailable.riskLevel, "UNAVAILABLE");
  assert.equal(unavailable.riskScore, null);

  const high = normalizeAiFields({
    ai_risk_level: "high",
    ai_risk_score: 0.874,
    ai_notes: "Severe chest pain with dizziness",
    ai_recommended_action: "Call doctor today",
    ai_processed_at: "2026-11-10T10:05:00Z",
  });
  assert.equal(high.ready, true);
  assert.equal(high.riskLevel, "HIGH");
  assert.equal(high.riskScore, 87);
  assert.equal(high.reason, "Severe chest pain with dizziness");
  assert.equal(high.recommendation, "Call doctor today");
});

test("normalizeCheckin maps Patient.id and preserves backend duration/adherence", () => {
  const normalized = normalizeCheckin({
    id: 77,
    patient: 42,
    patient_name: "Asha Rao",
    checkin_date: "2026-11-10",
    created_at: "2026-11-10T09:15:00Z",
    symptoms: [{ name: "Headache", severity: "MODERATE" }],
    mood: "not_good",
    pain_level: 5,
    symptom_duration: "SINCE_YESTERDAY",
    medication_adherence: "PARTIAL",
    notes: "Woke up dizzy",
    ai_risk_level: "medium",
    ai_risk_score: 0.62,
    ai_notes: "Moderate neurological symptoms",
    ai_recommended_action: "Monitor closely",
  });

  assert.equal(normalized.id, 77);
  assert.equal(normalized.patientId, 42);
  assert.equal(normalized.date, "2026-11-10T09:15:00Z");
  assert.equal(normalized.overallFeeling, "NOT_GOOD");
  assert.equal(normalized.duration, "SINCE_YESTERDAY");
  assert.equal(normalized.medicationAdherence, "PARTIAL");
  assert.equal(normalized.riskLevel, "MEDIUM");
  assert.equal(normalized.riskScore, 62);
});

test("submitCheckin, getCheckins, and waitForCheckinResult integrate live endpoints", async () => {
  store.clear();
  setStoredAuth({
    role: "PATIENT",
    user: { id: 10, role: "PATIENT" },
    token: makeLiveToken("patient", 10),
    refreshToken: makeLiveToken("patient", 10),
  });

  let postedBody = null;
  let pollCount = 0;
  globalThis.fetch = async (url, opts = {}) => {
    const u = String(url);
    if (u.endsWith("/checkins/") && opts.method === "POST") {
      postedBody = JSON.parse(opts.body);
      return new Response(
        JSON.stringify({
          id: 91,
          patient: 55,
          checkin_date: postedBody.checkin_date,
          created_at: "2026-11-10T10:00:00Z",
          symptoms: postedBody.symptoms,
          mood: postedBody.mood,
          pain_level: postedBody.pain_level,
          symptom_duration: postedBody.symptom_duration,
          medication_adherence: postedBody.medication_adherence,
          ai_risk_level: "pending",
        }),
        { status: 201, headers: { "Content-Type": "application/json" } }
      );
    }
    if (u.endsWith("/checkins/91/")) {
      pollCount += 1;
      if (pollCount === 1) {
        return new Response(JSON.stringify({ id: 91, ai_risk_level: "pending" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }
      return new Response(
        JSON.stringify({
          id: 91,
          ai_risk_level: "high",
          ai_risk_score: 0.89,
          ai_notes: "Escalated chest symptom",
          ai_recommended_action: "Seek urgent evaluation",
          ai_processed_at: "2026-11-10T10:00:02Z",
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      );
    }
    if (u.endsWith("/checkins/?patient=55")) {
      return new Response(
        JSON.stringify({
          results: [{ id: 91, patient: 55, checkin_date: "2026-11-10", symptoms: [], ai_risk_level: "high", ai_risk_score: 0.89 }],
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      );
    }
    throw new Error(`Unexpected fetch: ${opts.method || "GET"} ${u}`);
  };

  const created = await submitCheckin({
    patientId: 55,
    overallFeeling: "NOT_GOOD",
    symptoms: [{ name: "Chest Pain", severity: "SEVERE" }],
    duration: "JUST_STARTED",
    medicationAdherence: "MISSED",
    notes: "Started 20m ago",
  });
  assert.equal(postedBody.mood, "not_good");
  assert.equal(postedBody.pain_level, 8);
  assert.equal(postedBody.symptom_duration, "JUST_STARTED");
  assert.equal(postedBody.medication_adherence, "MISSED");
  assert.equal(created.patientId, 55);
  assert.equal(created.riskLevel, "PENDING");

  const finalResult = await waitForCheckinResult(91, { attempts: 3, delayMs: 1 });
  assert.equal(pollCount, 2);
  assert.equal(finalResult.ready, true);
  assert.equal(finalResult.riskLevel, "HIGH");
  assert.equal(finalResult.riskScore, 89);

  // Timeout stays PENDING (never fabricated LOW)
  globalThis.fetch = async () =>
    new Response(JSON.stringify({ id: 92, ai_risk_level: "pending" }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  const timedOut = await waitForCheckinResult(92, { attempts: 2, delayMs: 1 });
  assert.equal(timedOut.ready, false);
  assert.equal(timedOut.riskLevel, "PENDING");
  assert.equal(timedOut.riskScore, null);
});

test("getAlerts and normalizePatient avoid fabricated defaults when backend fields are empty", async () => {
  const emptyPatient = normalizePatient({ id: 12, full_name: "Kiran", user: 99 });
  assert.equal(emptyPatient.riskLevel, null);
  assert.equal(emptyPatient.riskScore, null);
  assert.equal(emptyPatient.medicationAdherencePct, null);

  setStoredAuth({
    role: "DOCTOR",
    user: { id: 4, role: "DOCTOR" },
    token: makeLiveToken("doctor", 4),
    refreshToken: makeLiveToken("doctor", 4),
  });
  globalThis.fetch = async () =>
    new Response(
      JSON.stringify({
        results: [
          {
            id: 5,
            patient: 12,
            checkin: 91,
            patient_name: "Kiran",
            severity: "high",
            reason: "Severe chest pain",
            status: "open",
            created_at: "2026-11-10T10:00:05Z",
          },
        ],
      }),
      { status: 200, headers: { "Content-Type": "application/json" } }
    );
  const alerts = await getAlerts();
  assert.equal(alerts.length, 1);
  assert.equal(alerts[0].patientId, 12);
  assert.equal(alerts[0].checkinId, 91);
  assert.equal(alerts[0].riskLevel, "HIGH");
  assert.equal(alerts[0].riskScore, null);
  assert.equal(alerts[0].status, "ACTIVE");
});

