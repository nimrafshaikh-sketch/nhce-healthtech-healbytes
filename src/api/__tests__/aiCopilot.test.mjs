import test from "node:test";
import assert from "node:assert/strict";

function createStorage() {
  const store = new Map();
  return {
    getItem(k) {
      return store.has(k) ? store.get(k) : null;
    },
    setItem(k, v) {
      store.set(k, String(v));
    },
    removeItem(k) {
      store.delete(k);
    },
    clear() {
      store.clear();
    },
  };
}

function makeJwt(payload) {
  const header = Buffer.from(JSON.stringify({ alg: "HS256", typ: "JWT" })).toString("base64url");
  const body = Buffer.from(JSON.stringify(payload)).toString("base64url");
  return `${header}.${body}.sig`;
}

globalThis.localStorage = createStorage();
globalThis.window = {
  dispatchEvent() {},
};
process.env.VITE_USE_MOCK_DATA = "false";
process.env.VITE_API_BASE_URL = "http://localhost:8000/api";

const client = await import("../client.js");
const aiApi = await import("../ai.api.js");

test("getAiEngineBaseUrl reads VITE_AI_ENGINE_URL and trims trailing slashes", () => {
  const prev = process.env.VITE_AI_ENGINE_URL;
  try {
    delete process.env.VITE_AI_ENGINE_URL;
    assert.equal(aiApi.getAiEngineBaseUrl(), "http://localhost:8001");

    process.env.VITE_AI_ENGINE_URL = "https://ai.healbytes.example///";
    assert.equal(aiApi.getAiEngineBaseUrl(), "https://ai.healbytes.example");
  } finally {
    if (prev === undefined) delete process.env.VITE_AI_ENGINE_URL;
    else process.env.VITE_AI_ENGINE_URL = prev;
  }
});

test("queryDoctorAgent uses configured VITE_AI_ENGINE_URL and sends bearer token", async () => {
  const now = Math.floor(Date.now() / 1000);
  const validAccess = makeJwt({ user_id: 2, role: "doctor", exp: now + 600 });
  client.setStoredAuth({
    role: "DOCTOR",
    token: validAccess,
    refreshToken: makeJwt({ user_id: 2, exp: now + 3600 }),
    user: { id: 2, role: "DOCTOR" },
  });

  const prevUrl = process.env.VITE_AI_ENGINE_URL;
  const origFetch = globalThis.fetch;
  const calls = [];
  process.env.VITE_AI_ENGINE_URL = "https://copilot.healbytes.test/";
  globalThis.fetch = async (url, opts) => {
    calls.push({ url, opts });
    return {
      ok: true,
      status: 200,
      async json() {
        return { reply: "Active medication: Metformin 500mg.", tool_calls: [{ tool_name: "get_patient_medications" }] };
      },
    };
  };

  try {
    const res = await aiApi.queryDoctorAgent({ patientId: 42, message: "Active meds?" });
    assert.equal(res.reply, "Active medication: Metformin 500mg.");
    assert.equal(calls.length, 1);
    assert.equal(calls[0].url, "https://copilot.healbytes.test/api/v1/agents/doctor");
    assert.equal(calls[0].opts.headers.Authorization, `Bearer ${validAccess}`);
    const body = JSON.parse(calls[0].opts.body);
    assert.equal(body.patient_id, "42");
    assert.equal(body.auth_token, validAccess);
  } finally {
    globalThis.fetch = origFetch;
    if (prevUrl === undefined) delete process.env.VITE_AI_ENGINE_URL;
    else process.env.VITE_AI_ENGINE_URL = prevUrl;
  }
});

test("queryReceptionistAgent refreshes expired token before calling AI engine", async () => {
  const now = Math.floor(Date.now() / 1000);
  const expiredAccess = makeJwt({ user_id: 3, role: "receptionist", exp: now - 30 });
  const freshAccess = makeJwt({ user_id: 3, role: "receptionist", exp: now + 600 });
  const validRefresh = makeJwt({ user_id: 3, role: "receptionist", exp: now + 3600 });

  client.setStoredAuth({
    role: "RECEPTIONIST",
    token: expiredAccess,
    refreshToken: validRefresh,
    user: { id: 3, role: "RECEPTIONIST" },
  });

  const prevUrl = process.env.VITE_AI_ENGINE_URL;
  const origFetch = globalThis.fetch;
  const calls = [];
  process.env.VITE_AI_ENGINE_URL = "https://copilot.healbytes.test";
  globalThis.fetch = async (url, opts) => {
    calls.push({ url, opts });
    if (url.endsWith("/auth/login/refresh/")) {
      return {
        ok: true,
        status: 200,
        async json() {
          return { access: freshAccess, refresh: validRefresh };
        },
      };
    }
    return {
      ok: true,
      status: 200,
      async json() {
        return { reply: "2 appointments scheduled today.", tool_calls: [] };
      },
    };
  };

  try {
    const res = await aiApi.queryReceptionistAgent({ message: "Today's appointments?" });
    assert.equal(res.reply, "2 appointments scheduled today.");
    assert.equal(calls.length, 2);
    assert.equal(calls[0].url, "http://localhost:8000/api/auth/login/refresh/");
    assert.equal(calls[1].url, "https://copilot.healbytes.test/api/v1/agents/receptionist");
    assert.equal(calls[1].opts.headers.Authorization, `Bearer ${freshAccess}`);
  } finally {
    globalThis.fetch = origFetch;
    if (prevUrl === undefined) delete process.env.VITE_AI_ENGINE_URL;
    else process.env.VITE_AI_ENGINE_URL = prevUrl;
  }
});

test("agent errors map 503, 502, and network offline states to user-friendly messages", async () => {
  const now = Math.floor(Date.now() / 1000);
  client.setStoredAuth({
    role: "DOCTOR",
    token: makeJwt({ user_id: 2, role: "doctor", exp: now + 600 }),
    refreshToken: makeJwt({ user_id: 2, exp: now + 3600 }),
    user: { id: 2, role: "DOCTOR" },
  });

  const origFetch = globalThis.fetch;
  try {
    globalThis.fetch = async () => ({
      ok: false,
      status: 503,
      async json() {
        return { detail: "GEMINI_API_KEY is not configured" };
      },
    });
    await assert.rejects(
      () => aiApi.queryDoctorAgent({ patientId: 1, message: "Hi" }),
      (err) => err.status === 503 && /currently offline/i.test(err.message)
    );

    globalThis.fetch = async () => ({
      ok: false,
      status: 502,
      async json() {
        return { detail: "Upstream quota exceeded" };
      },
    });
    await assert.rejects(
      () => aiApi.queryReceptionistAgent({ message: "Hi" }),
      (err) => err.status === 502 && /could not reach the AI model provider/i.test(err.message)
    );

    globalThis.fetch = async () => {
      throw new TypeError("Failed to fetch");
    };
    await assert.rejects(
      () => aiApi.queryDoctorAgent({ patientId: 1, message: "Hi" }),
      (err) => err.code === "NETWORK_ERROR" && /offline or unreachable/i.test(err.message)
    );
  } finally {
    globalThis.fetch = origFetch;
  }
});

