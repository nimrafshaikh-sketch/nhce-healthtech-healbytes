// Centralized network layer. Everything else (components, contexts) goes
// through the api/*.js files, never fetch() directly.
export const USE_MOCK = String(import.meta.env.VITE_USE_MOCK_DATA) !== "false";
export const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:4000/api";
const AUTH_STORAGE_KEY = "healbytes_auth"; // see context/AuthContext.jsx - same key

// Auth was previously threaded manually per call site, and almost none of
// the api/*.js modules actually did it (only documents.api.js read the
// token itself, ad hoc) - every other "live mode" call was silently
// missing its Authorization header and would 401 against the real
// backend. Reading it here once, centrally, fixes that for every caller;
// an explicit `token` option (e.g. right after redeeming an invitation,
// before AuthContext has persisted anything yet) still overrides this.
function currentToken() {
  try {
    const raw = localStorage.getItem(AUTH_STORAGE_KEY);
    return raw ? JSON.parse(raw).token : null;
  } catch {
    return null;
  }
}

export async function apiFetch(path, { method = "GET", body, token } = {}) {
  const authToken = token !== undefined ? token : currentToken();
  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    const message =
      errorBody.detail || errorBody.message ||
      (typeof errorBody === "object" ? Object.values(errorBody).flat().join(" ") : "") ||
      `Request failed (${res.status})`;
    const err = new Error(message);
    err.status = res.status;
    throw err;
  }
  if (res.status === 204) return null;
  return res.json();
}

export function mockDelay(ms = 500) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
