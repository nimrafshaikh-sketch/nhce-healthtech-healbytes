import { apiFetch, USE_MOCK, mockDelay } from "./client";

export async function orderLabTest({ patientId, testName, priority = "routine", notes = "" }) {
  if (USE_MOCK) {
    await mockDelay(300);
    return {
      id: Math.floor(Math.random() * 1000) + 1,
      patient: patientId,
      test_name: testName,
      priority,
      notes,
      status: "requested",
      created_at: new Date().toISOString(),
    };
  }
  return apiFetch("/labtests/requests/", {
    method: "POST",
    body: {
      patient: Number(patientId),
      test_name: testName,
      priority,
      notes,
    },
  });
}

export async function getLabRequests(patientId) {
  if (USE_MOCK) {
    await mockDelay(200);
    return [];
  }
  const endpoint = patientId ? `/labtests/requests/?patient=${patientId}` : "/labtests/requests/";
  const data = await apiFetch(endpoint);
  return Array.isArray(data) ? data : data.results || [];
}

export async function claimLabRequest(requestId) {
  if (USE_MOCK) {
    await mockDelay(250);
    return { id: requestId, status: "in_progress" };
  }
  return apiFetch(`/labtests/requests/${requestId}/claim/`, { method: "POST" });
}

export async function recordLabResult(requestId, { resultText, notes = "" }) {
  if (USE_MOCK) {
    await mockDelay(300);
    return { id: requestId, result_text: resultText, notes, status: "completed" };
  }
  return apiFetch(`/labtests/requests/${requestId}/result/`, {
    method: "POST",
    body: {
      result_text: resultText,
      notes,
    },
  });
}
