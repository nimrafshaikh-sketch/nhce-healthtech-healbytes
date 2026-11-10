import test from "node:test";
import assert from "node:assert/strict";

// Minimal browser globals for testing client.js in live mode
const store = new Map();
globalThis.localStorage = {
  getItem: (k) => (store.has(k) ? store.get(k) : null),
  setItem: (k, v) => store.set(k, String(v)),
  removeItem: (k) => store.delete(k),
  clear: () => store.clear(),
};

const dispatchedEvents = [];
globalThis.window = {
  dispatchEvent: (ev) => dispatchedEvents.push(ev.type),
  addEventListener: () => {},
  removeEventListener: () => {},
};
globalThis.CustomEvent = class CustomEvent {
  constructor(type, init = {}) {
    this.type = type;
    this.detail = init.detail;
  }
};
globalThis.Event = class Event {
  constructor(type) {
    this.type = type;
  }
};

function makeJwt(payloadObj) {
  const header = Buffer.from(JSON.stringify({ alg: "HS256", typ: "JWT" })).toString("base64url");
  const payload = Buffer.from(JSON.stringify(payloadObj)).toString("base64url");
  return `${header}.${payload}.sig`;
}

// Import client.js (with import.meta.env stubbed via loader or direct module import)
import {
  AUTH_STORAGE_KEY,
  DATA_STORAGE_KEY,
  getStoredAuth,
  setStoredAuth,
  clearStoredAuth,
  isJwtExpired,
  apiFetch,
} from "../client.js";
import { uploadDocument, getDocumentViewUrl } from "../documents.api.js";

test("mode mismatch purges mock demo tokens in live mode", () => {
  store.clear();
  localStorage.setItem(
    AUTH_STORAGE_KEY,
    JSON.stringify({ role: "DOCTOR", token: "demo-doctor-token", mode: "mock" })
  );
  localStorage.setItem(DATA_STORAGE_KEY, JSON.stringify({ patients: [{ id: 1 }] }));

  const loaded = getStoredAuth();
  assert.equal(loaded, null);
  assert.equal(localStorage.getItem(AUTH_STORAGE_KEY), null);
  assert.equal(localStorage.getItem(DATA_STORAGE_KEY), null);
});

test("expired access token triggers single-flight refresh and retries original request", async () => {
  store.clear();
  dispatchedEvents.length = 0;

  const nowSec = Math.floor(Date.now() / 1000);
  const expiredAccess = makeJwt({ user_id: 7, role: "patient", exp: nowSec - 60 });
  const validRefresh = makeJwt({ user_id: 7, token_type: "refresh", exp: nowSec + 86400 });
  const freshAccess = makeJwt({ user_id: 7, role: "patient", exp: nowSec + 3600 });
  const freshRefresh = makeJwt({ user_id: 7, token_type: "refresh", exp: nowSec + 86400 * 7 });

  setStoredAuth({
    role: "PATIENT",
    user: { id: 7, role: "PATIENT" },
    token: expiredAccess,
    refreshToken: validRefresh,
  });

  let refreshCalls = 0;
  globalThis.fetch = async (url, opts = {}) => {
    if (String(url).endsWith("/auth/login/refresh/")) {
      refreshCalls += 1;
      await new Promise((r) => setTimeout(r, 15));
      return new Response(
        JSON.stringify({ access: freshAccess, refresh: freshRefresh }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      );
    }
    if (String(url).endsWith("/auth/me/")) {
      assert.equal(opts.headers.Authorization, `Bearer ${freshAccess}`);
      return new Response(
        JSON.stringify({ id: 7, role: "patient", email: "p@example.com" }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      );
    }
    throw new Error(`Unexpected URL: ${url}`);
  };

  // Fire two concurrent requests while access token is expired
  const [r1, r2] = await Promise.all([apiFetch("/auth/me/"), apiFetch("/auth/me/")]);
  assert.equal(refreshCalls, 1, "concurrent expired calls must share one refresh request");
  assert.equal(r1.id, 7);
  assert.equal(r2.id, 7);

  const persisted = getStoredAuth();
  assert.equal(persisted.token, freshAccess);
  assert.equal(persisted.refreshToken, freshRefresh);
  assert.ok(dispatchedEvents.includes("healbytes:auth-refreshed"));
});

test("invalid refresh token clears auth and cached clinical data without looping", async () => {
  store.clear();
  dispatchedEvents.length = 0;

  const nowSec = Math.floor(Date.now() / 1000);
  const access = makeJwt({ user_id: 3, role: "doctor", exp: nowSec + 3600 });
  const refresh = makeJwt({ user_id: 3, token_type: "refresh", exp: nowSec + 86400 });

  setStoredAuth({
    role: "DOCTOR",
    user: { id: 3, role: "DOCTOR" },
    token: access,
    refreshToken: refresh,
  });
  localStorage.setItem(DATA_STORAGE_KEY, JSON.stringify({ patients: [{ id: 99 }] }));

  let refreshAttempts = 0;
  globalThis.fetch = async (url) => {
    if (String(url).endsWith("/auth/login/refresh/")) {
      refreshAttempts += 1;
      return new Response(JSON.stringify({ detail: "Token is invalid or expired" }), {
        status: 401,
        headers: { "Content-Type": "application/json" },
      });
    }
    return new Response(JSON.stringify({ detail: "Token invalid" }), {
      status: 401,
      headers: { "Content-Type": "application/json" },
    });
  };

  await assert.rejects(() => apiFetch("/patients/"), (err) => err.status === 401);
  assert.equal(refreshAttempts, 1);
  assert.equal(localStorage.getItem(AUTH_STORAGE_KEY), null);
  assert.equal(localStorage.getItem(DATA_STORAGE_KEY), null);
  assert.ok(dispatchedEvents.includes("healbytes:auth-cleared"));
});

test("clearStoredAuth removes both auth and clinical data caches", () => {
  store.clear();
  localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify({ token: "abc" }));
  localStorage.setItem(DATA_STORAGE_KEY, JSON.stringify({ patients: [1, 2] }));
  clearStoredAuth();
  assert.equal(localStorage.getItem(AUTH_STORAGE_KEY), null);
  assert.equal(localStorage.getItem(DATA_STORAGE_KEY), null);
  assert.equal(isJwtExpired("not-a-jwt"), false);
});

test("uploadDocument refreshes expired token and ignores mode-mismatched mock token", async () => {
  store.clear();
  dispatchedEvents.length = 0;

  // Switching from mock to live must ignore demo token for document view URL too
  localStorage.setItem(
    AUTH_STORAGE_KEY,
    JSON.stringify({ role: "PATIENT", token: "demo-patient-token", mode: "mock" })
  );
  assert.equal(getDocumentViewUrl(42), "http://localhost:8000/api/documents/42/view/");

  const nowSec = Math.floor(Date.now() / 1000);
  const expiredAccess = makeJwt({ user_id: 9, role: "patient", exp: nowSec - 30 });
  const validRefresh = makeJwt({ user_id: 9, token_type: "refresh", exp: nowSec + 86400 });
  const freshAccess = makeJwt({ user_id: 9, role: "patient", exp: nowSec + 3600 });

  setStoredAuth({
    role: "PATIENT",
    user: { id: 9, role: "PATIENT" },
    token: expiredAccess,
    refreshToken: validRefresh,
  });

  let uploadCalls = 0;
  globalThis.fetch = async (url, opts = {}) => {
    if (String(url).endsWith("/auth/login/refresh/")) {
      return new Response(JSON.stringify({ access: freshAccess }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }
    if (String(url).endsWith("/documents/upload/")) {
      uploadCalls += 1;
      assert.equal(opts.headers.Authorization, `Bearer ${freshAccess}`);
      return new Response(JSON.stringify({ id: 55, title: "Lab" }), {
        status: 201,
        headers: { "Content-Type": "application/json" },
      });
    }
    throw new Error(`Unexpected URL: ${url}`);
  };

  const form = new FormData();
  form.append("title", "Lab");
  const uploaded = await uploadDocument(form);
  assert.equal(uploadCalls, 1);
  assert.equal(uploaded.id, 55);
  assert.equal(getDocumentViewUrl(55), `http://localhost:8000/api/documents/55/view/?token=${encodeURIComponent(freshAccess)}`);
});

