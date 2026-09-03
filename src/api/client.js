// Centralized network layer. Everything else (components, contexts) goes
// through the api/*.js files, never fetch() directly.
export const USE_MOCK = String(import.meta.env.VITE_USE_MOCK_DATA) !== "false";
const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:4000/api";

export async function apiFetch(path, { method = "GET", body, token } = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new Error(errorBody.message || `Request failed (${res.status})`);
  }
  if (res.status === 204) return null;
  return res.json();
}

export function mockDelay(ms = 500) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
