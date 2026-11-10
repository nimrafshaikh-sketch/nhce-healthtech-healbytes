import {
  apiFetch,
  USE_MOCK,
  mockDelay,
  BASE_URL,
  currentToken,
  isJwtExpired,
  refreshAccessToken,
} from "./client.js";

export async function uploadDocument(formData, _retried = false) {
  if (USE_MOCK) {
    await mockDelay(600);
    return {
      id: Math.floor(Math.random() * 1000) + 1,
      title: formData.get("title") || "Medical Document",
      document_type: formData.get("document_type") || "LAB_REPORT",
      processing_status: "processed",
      extraction_status: formData.get("document_type") === "PRESCRIPTION" ? "review_required" : "processed",
      extracted_text: "Sample extracted clinical text",
      extracted_data: { clinical_findings: [] },
      view_url: "#",
      created_at: new Date().toISOString(),
    };
  }

  // Use raw fetch for multipart/form-data while sharing the single-flight JWT lifecycle
  let token = currentToken();
  if (token && isJwtExpired(token)) {
    const renewed = await refreshAccessToken();
    if (renewed) token = renewed;
  }
  const headers = token ? { Authorization: `Bearer ${token}` } : {};

  const response = await fetch(`${BASE_URL}/documents/upload/`, {
    method: "POST",
    headers,
    body: formData,
  });

  if (response.status === 401 && !_retried) {
    const renewed = await refreshAccessToken();
    if (renewed) {
      return uploadDocument(formData, true);
    }
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    const err = new Error(errorData.detail || errorData.message || `Upload failed with status ${response.status}`);
    err.status = response.status;
    throw err;
  }
  return response.json();
}

// Bug fix: the only call site (PatientProfile.jsx) passes {patientId: id},
// but this accepted a bare `patientId` positional argument - the object was
// truthy, so it silently built `/documents/?patient=[object Object]` in
// live mode (mock mode masked this, since it always just returns []).
export async function getDocuments({ patientId } = {}) {
  if (USE_MOCK) {
    await mockDelay(300);
    return [];
  }
  const endpoint = patientId && patientId !== "undefined" ? `/documents/?patient=${patientId}` : "/documents/";
  const data = await apiFetch(endpoint);
  return Array.isArray(data) ? data : data.results || [];
}

export async function getDocumentDetail(documentId) {
  if (USE_MOCK) {
    await mockDelay(200);
    return null;
  }
  return apiFetch(`/documents/${documentId}/`);
}

export async function verifyPrescriptionDocument(documentId, data) {
  if (USE_MOCK) {
    await mockDelay(400);
    return { detail: "Prescription verified.", medication: data };
  }
  return apiFetch(`/documents/${documentId}/verify-prescription/`, {
    method: "POST",
    body: data,
  });
}

export function getDocumentViewUrl(documentId) {
  const token = currentToken();
  if (token) {
    return `${BASE_URL}/documents/${documentId}/view/?token=${encodeURIComponent(token)}`;
  }
  return `${BASE_URL}/documents/${documentId}/view/`;
}
