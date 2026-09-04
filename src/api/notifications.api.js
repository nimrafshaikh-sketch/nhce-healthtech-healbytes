import { apiFetch, USE_MOCK, mockDelay } from "./client";
import { ENDPOINTS } from "./endpoints";

// The backend (apps.notifications) already models in-app Notification rows
// - including the new "lab_test_request" type fired when a doctor orders a
// test (see apps/labtests/tasks.py::notify_lab_techs_of_new_request) - but
// nothing in the frontend ever read this endpoint. This is the first
// consumer, used for a small unread-count badge (Part 6/7's "dashboard
// notification/badge" requirement) rather than building a second,
// duplicate notification system.
export async function getUnreadNotificationCount() {
  if (USE_MOCK) {
    await mockDelay(150);
    return 0;
  }
  const data = await apiFetch(ENDPOINTS.NOTIFICATIONS_UNREAD);
  const list = Array.isArray(data) ? data : data.results || [];
  return list.length;
}

export async function getNotifications({ unreadOnly = false } = {}) {
  if (USE_MOCK) {
    await mockDelay(150);
    return [];
  }
  const data = await apiFetch(unreadOnly ? ENDPOINTS.NOTIFICATIONS_UNREAD : ENDPOINTS.NOTIFICATIONS);
  return Array.isArray(data) ? data : data.results || [];
}

export async function markNotificationRead(id) {
  if (USE_MOCK) {
    await mockDelay(150);
    return { id, is_read: true };
  }
  return apiFetch(ENDPOINTS.NOTIFICATION_READ(id), { method: "POST" });
}
