import { apiFetch, USE_MOCK, mockDelay } from "./client";

export async function orderLabTest(data) {
  const patientId = data.patientId || data.patient;
  const testName = data.testName || data.test_name || data.testType;
  const priority = data.priority || "routine";
  const notes = data.notes || "";

  if (USE_MOCK) {
    await mockDelay(300);
    return {
      id: Math.floor(Math.random() * 1000) + 1,
      patient: patientId,
      patientId,
      test_name: testName,
      testName,
      priority,
      notes,
      status: "requested",
      createdAt: new Date().toISOString(),
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

export async function getLabQueue() {
  return getLabRequests();
}

export async function updateLabTestStatus(reqId, status) {
  if (status === "in_progress") {
    return claimLabRequest(reqId);
  }
  return { id: reqId, status };
}

export async function submitLabResult(reqId, resultData) {
  return recordLabResult(reqId, {
    resultText: resultData.resultText || resultData.result_text || JSON.stringify(resultData),
    notes: resultData.notes || "",
  });
}

export async function getLabResultsForPatient(patientId) {
  return getLabRequests(patientId);
}

export async function reviewLabResult(resultId) {
  if (USE_MOCK) {
    await mockDelay(250);
    return { id: resultId, reviewed_at: new Date().toISOString() };
  }
  return apiFetch(`/labtests/results/${resultId}/review/`, { method: "POST" });
}

