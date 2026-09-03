// Single place to edit endpoint paths so they can be matched to the real
// backend without touching any component or context.
export const ENDPOINTS = {
  AUTH_LOGIN: "/auth/login",
  AUTH_ME: "/auth/me",
  PATIENTS: "/patients",
  PATIENT_BY_ID: (id) => `/patients/${id}`,
  INVITATIONS: "/invitations",
  INVITATIONS_VERIFY: "/invitations/verify",
  CHECKINS: "/checkins",
  CHECKINS_BY_PATIENT: (id) => `/checkins/patient/${id}`,
  AI_ANALYZE_CHECKIN: "/ai/analyze-checkin",
  MEDICATIONS_BY_PATIENT: (id) => `/patients/${id}/medications`,
  MEDICATION_TAKEN: (id) => `/medications/${id}/taken`,
  ALERTS: "/alerts",
  ALERT_RESOLVE: (id) => `/alerts/${id}/resolve`,
  ANALYTICS_PATIENT: (id) => `/analytics/patient/${id}`,
  ANALYTICS_DOCTOR: "/analytics/doctor",
  QR_GENERATE: "/qr/generate",
  QR_VERIFY: "/qr/verify",
};
