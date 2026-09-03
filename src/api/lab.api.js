import { apiFetch, USE_MOCK, mockDelay } from "./client";
import { initialLabRequests, initialLabResults } from "../data/demoData";

let mockLabRequests = [...initialLabRequests];
let mockLabResults = [...initialLabResults];

export async function orderLabTest(data) {
  if (USE_MOCK) {
    await mockDelay(600);
    const newReq = {
      id: `req_${Date.now()}`,
      status: "REQUESTED",
      createdAt: new Date().toISOString(),
      ...data,
    };
    mockLabRequests.unshift(newReq);
    return newReq;
  }
  return apiFetch(`/lab/requests`, { method: "POST", body: data });
}

export async function getLabQueue() {
  if (USE_MOCK) {
    await mockDelay(500);
    return [...mockLabRequests];
  }
  return apiFetch(`/lab/queue`);
}

export async function updateLabTestStatus(reqId, status) {
  if (USE_MOCK) {
    await mockDelay(400);
    const req = mockLabRequests.find((r) => r.id === reqId);
    if (req) req.status = status;
    return req;
  }
  return apiFetch(`/lab/requests/${reqId}/status`, { method: "PUT", body: { status } });
}

export async function submitLabResult(reqId, resultData) {
  if (USE_MOCK) {
    await mockDelay(1000);
    const req = mockLabRequests.find((r) => r.id === reqId);
    if (req) {
      req.status = "COMPLETED";
      const newResult = {
        id: `res_${Date.now()}`,
        patientId: req.patientId,
        doctorId: req.doctorId,
        testType: req.testType,
        status: "COMPLETED",
        releaseStatus: "READY", // Needs doctor review
        date: new Date().toISOString(),
        ...resultData,
      };
      mockLabResults.unshift(newResult);
      return newResult;
    }
    throw new Error("Request not found");
  }
  return apiFetch(`/lab/requests/${reqId}/results`, { method: "POST", body: resultData });
}

export async function getLabResultsForPatient(patientId) {
  if (USE_MOCK) {
    await mockDelay(400);
    return mockLabResults.filter((r) => r.patientId === patientId);
  }
  return apiFetch(`/patients/${patientId}/lab-results`);
}
