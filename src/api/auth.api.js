import { apiFetch, USE_MOCK, mockDelay } from "./client";
import { ENDPOINTS } from "./endpoints";
import { demoDoctor, initialPatients } from "../data/demoData";

export async function login({ role, email, password }) {
  if (USE_MOCK) {
    await mockDelay(600);
    if (role === "DOCTOR") {
      return { token: "demo-doctor-token", user: demoDoctor };
    }
    const patient =
      initialPatients.find((p) => p.email.toLowerCase() === String(email).toLowerCase()) ||
      initialPatients[0];
    return { token: "demo-patient-token", user: patient };
  }
  const data = await apiFetch(ENDPOINTS.AUTH_LOGIN, { method: "POST", body: { email, password } });
  return { token: data.access || data.token, user: data.user };
}
