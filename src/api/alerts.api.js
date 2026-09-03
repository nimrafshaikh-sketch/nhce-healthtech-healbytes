import { apiFetch, USE_MOCK, mockDelay } from "./client";
import { ENDPOINTS } from "./endpoints";

export async function resolveAlert(alertId) {
  if (USE_MOCK) {
    await mockDelay(300);
    return { id: alertId, status: "RESOLVED" };
  }
  return apiFetch(ENDPOINTS.ALERT_RESOLVE(alertId), { method: "PUT" });
}
