import { apiFetch, USE_MOCK, mockDelay } from "./client";
import { ENDPOINTS } from "./endpoints";
import { generateId } from "../utils/id";

export async function submitCheckin(payload) {
  if (USE_MOCK) {
    await mockDelay(300);
    return { id: generateId("chk"), date: new Date(), ...payload };
  }
  return apiFetch(ENDPOINTS.CHECKINS, { method: "POST", body: payload });
}
