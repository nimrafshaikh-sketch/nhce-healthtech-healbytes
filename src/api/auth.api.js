import { apiFetch, USE_MOCK, mockDelay } from "./client";
import { ENDPOINTS } from "./endpoints";
import { demoDoctor, demoReceptionist, demoLabTech, initialPatients } from "../data/demoData";

// Django's UserSerializer (apps.accounts.serializers) returns
// {id, email, username, first_name, last_name, role, phone_number,
// specialization, license_number, date_joined} - no `name`/`avatarInitials`,
// which most components read directly (e.g. dashboard greetings). Normalize
// once here so every consumer of AuthContext's `user` can keep using
// `user.name` regardless of whether the session came from mock or live data.
function normalizeUser(raw) {
  if (!raw) return raw;
  const name = [raw.first_name, raw.last_name].filter(Boolean).join(" ") || raw.username || raw.email;
  const avatarInitials = name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0].toUpperCase())
    .join("");
  const role = raw.role ? String(raw.role).toUpperCase() : raw.role;
  return { ...raw, name, avatarInitials, role };
}

export async function login({ role, email, password }) {
  if (USE_MOCK) {
    await mockDelay(600);
    if (role === "DOCTOR") {
      return { token: "demo-doctor-token", user: demoDoctor };
    }
    if (role === "RECEPTIONIST") {
      return { token: "demo-receptionist-token", user: demoReceptionist };
    }
    if (role === "LAB_TECH") {
      return { token: "demo-lab-tech-token", user: demoLabTech };
    }
    // Match strictly by email - no fallback to initialPatients[0]. A
    // fallback here is the same class of bug as invitation.api.js's old
    // patients[0] fallback: it would silently log a patient in as someone
    // else's seeded demo record instead of failing loudly.
    const patient = initialPatients.find((p) => p.email.toLowerCase() === String(email).toLowerCase());
    if (!patient) {
      throw new Error("No account found for that email. Try demo emails like rahul.sharma@healbytes.demo.");
    }
    return { token: "demo-patient-token", user: patient };
  }
  const data = await apiFetch(ENDPOINTS.AUTH_LOGIN, { method: "POST", body: { email, password } });
  return { token: data.access || data.token, user: normalizeUser(data.user) };
}

export { normalizeUser };
