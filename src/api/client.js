// Centralized network layer. Everything else (components, contexts) goes
// through the api/*.js files, never fetch() directly.
const env = (typeof import.meta !== "undefined" && import.meta.env) || (typeof process !== "undefined" && process.env) || {};
export const USE_MOCK = String(env.VITE_USE_MOCK_DATA) !== "false";
export const BASE_URL = env.VITE_API_BASE_URL || "http://localhost:8000/api";
export const AUTH_STORAGE_KEY = "healbytes_auth"; // see context/AuthContext.jsx - same key
export const DATA_STORAGE_KEY = "healbytes_data";

const CURRENT_MODE = USE_MOCK ? "mock" : "live";

export function decodeJwtPayload(token) {
  if (!token || typeof token !== "string") return null;
  const parts = token.split(".");
  if (parts.length !== 3) return null;
  try {
    const base64 = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), "=");
    return JSON.parse(atob(padded));
  } catch {
    return null;
  }
}

export function isJwtExpired(token, skewSeconds = 15) {
  const payload = decodeJwtPayload(token);
  if (!payload || typeof payload.exp !== "number") return false;
  return Date.now() / 1000 >= payload.exp - skewSeconds;
}

export function clearStoredAuth() {
  try {
    localStorage.removeItem(AUTH_STORAGE_KEY);
    localStorage.removeItem(DATA_STORAGE_KEY);
  } catch {
    // ignore storage errors
  }
  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event("healbytes:auth-cleared"));
  }
}

export function getStoredAuth() {
  try {
    const raw = localStorage.getItem(AUTH_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!parsed || !parsed.token) return null;
    // Prevent mock tokens ("demo-*-token") from poisoning live mode or vice versa
    if (parsed.mode && parsed.mode !== CURRENT_MODE) {
      clearStoredAuth();
      return null;
    }
    if (!USE_MOCK && !decodeJwtPayload(parsed.token)) {
      clearStoredAuth();
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

export function setStoredAuth(value) {
  try {
    if (value && value.token) {
      localStorage.setItem(
        AUTH_STORAGE_KEY,
        JSON.stringify({ ...value, mode: CURRENT_MODE })
      );
    } else {
      clearStoredAuth();
    }
  } catch {
    // storage unavailable, continue in-memory
  }
}

export function currentToken() {
  const stored = getStoredAuth();
  return stored ? stored.token : null;
}

let refreshInFlight = null;

export async function refreshAccessToken() {
  if (USE_MOCK) return currentToken();
  if (refreshInFlight) return refreshInFlight;

  refreshInFlight = (async () => {
    const stored = getStoredAuth();
    const refreshToken = stored?.refreshToken;
    if (!refreshToken || isJwtExpired(refreshToken, 5)) {
      clearStoredAuth();
      return null;
    }

    try {
      const res = await fetch(`${BASE_URL}/auth/login/refresh/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh: refreshToken }),
      });
      if (!res.ok) {
        clearStoredAuth();
        return null;
      }
      const data = await res.json();
      if (!data?.access) {
        clearStoredAuth();
        return null;
      }
      const nextAuth = {
        ...stored,
        token: data.access,
        refreshToken: data.refresh || refreshToken,
        mode: CURRENT_MODE,
      };
      setStoredAuth(nextAuth);
      if (typeof window !== "undefined") {
        window.dispatchEvent(new CustomEvent("healbytes:auth-refreshed", { detail: nextAuth }));
      }
      return data.access;
    } catch {
      // Transient network error during refresh: do not destroy refreshToken unless server rejected it
      return null;
    } finally {
      refreshInFlight = null;
    }
  })();

  return refreshInFlight;
}

const NO_REFRESH_PATHS = new Set(["/auth/login/", "/auth/login/refresh/", "/auth/register/doctor/"]);

export async function apiFetch(path, { method = "GET", body, token, _retried = false } = {}) {
  const usesStoredSession = token === undefined;
  let authToken = usesStoredSession ? currentToken() : token;

  // Proactively renew expired access token before hitting protected endpoints
  if (!USE_MOCK && usesStoredSession && authToken && !NO_REFRESH_PATHS.has(path) && isJwtExpired(authToken)) {
    const renewed = await refreshAccessToken();
    if (renewed) {
      authToken = renewed;
    }
  }

  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });

  if (
    res.status === 401 &&
    !USE_MOCK &&
    usesStoredSession &&
    !_retried &&
    !NO_REFRESH_PATHS.has(path)
  ) {
    const renewed = await refreshAccessToken();
    if (renewed) {
      return apiFetch(path, { method, body, _retried: true });
    }
  }

  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    let message = "";
    if (typeof errorBody === "string") {
      message = errorBody;
    } else if (errorBody && typeof errorBody === "object") {
      if (typeof errorBody.detail === "string") {
        message = errorBody.detail;
      } else if (typeof errorBody.message === "string") {
        message = errorBody.message;
      } else {
        const parts = [];
        for (const [key, val] of Object.entries(errorBody)) {
          const prefix = ["detail", "message", "non_field_errors", "error"].includes(key) ? "" : `${key}: `;
          if (Array.isArray(val)) {
            parts.push(`${prefix}${val.map((v) => (typeof v === "object" ? JSON.stringify(v) : String(v))).join(" ")}`);
          } else if (typeof val === "object" && val !== null) {
            parts.push(`${prefix}${JSON.stringify(val)}`);
          } else {
            parts.push(`${prefix}${String(val)}`);
          }
        }
        message = parts.join(" ");
      }
    }
    if (!message) message = `Request failed (${res.status})`;
    const err = new Error(message);
    err.status = res.status;
    err.data = errorBody;
    throw err;
  }
  if (res.status === 204) return null;
  return res.json();
}

export function mockDelay(ms = 500) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
