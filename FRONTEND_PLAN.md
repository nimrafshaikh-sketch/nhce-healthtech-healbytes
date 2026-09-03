# HealBytes Frontend — Build Plan (Member 1: Ed)

Status check on `nhce-healthtech-healbytes`: the repo is currently empty (only `.git/` — no `package.json`, no source files). There is nothing to preserve from a "previous implementation." This plan starts from zero, which is actually simpler: no legacy code to reconcile.

This doc is the single source of truth I'll build against, and the contract I'm handing to Members 2–4 so nobody blocks anybody.

---

## 1. Stack decision

| Layer | Choice | Why |
|---|---|---|
| Build tool | Vite | Fastest dev loop for a 48h hackathon |
| Framework | React 18 (JSX, not TS) | TS adds friction we don't have time for |
| Routing | React Router v6 | Standard, small |
| Styling | Tailwind CSS | Fast to theme, no design-token boilerplate |
| Icons | lucide-react | Clean, matches "clinical not childish" direction |
| State | React Context + useReducer | No Redux needed at this scale |
| Charts (analytics only) | recharts | Small, only used in 2 low-priority screens |

No backend framework opinions here — that's Member 2/3's call entirely.

---

## 2. Folder structure

```
src/
├── api/                  # ALL network calls live here, nothing else touches fetch
│   ├── client.js         # base axios/fetch wrapper, reads VITE_API_BASE_URL
│   ├── auth.api.js
│   ├── patients.api.js
│   ├── invitation.api.js
│   ├── medication.api.js
│   ├── checkin.api.js
│   ├── alerts.api.js
│   ├── analytics.api.js
│   ├── qr.api.js
│   └── ai.api.js
├── services/
│   └── mockService.js    # demo data + demo risk logic, isolated, swappable
├── data/
│   └── demoData.js        # 8 seeded patients, varied risk/adherence
├── components/
│   ├── ui/                # Button, Input, Select, Modal, Badge, Avatar, EmptyState, LoadingState, Skeleton
│   ├── healthcare/        # RiskBadge, RiskScore, PatientCard, MedicationCard, AlertCard, HealthTrendCard, CheckinSummary, QRCard
│   └── layout/             # DoctorLayout, PatientLayout, DoctorSidebar, PatientBottomNav, Topbar
├── context/                # AuthContext, DemoDataContext (shared state for the wow-moment flow)
├── hooks/
├── pages/
│   ├── doctor/
│   └── patient/
├── router/
└── App.jsx
```

Every API file exports functions that internally check `VITE_USE_MOCK_DATA` and either hit `mockService` or call the real endpoint. Components never know which one is running — this is what makes backend integration a one-line env flip later.

---

## 3. Design system (locked, so nothing looks inconsistent across screens)

- **Primary**: deep teal/emerald (`#0F6E5E`-ish family)
- **Background**: warm off-white, soft neutral gray surfaces — no navy, no glass
- **Risk semantics**: green = low, amber = medium, red = high — used only where risk is actually being shown, never decoratively
- **Typography**: one clear heading scale, comfortable body size, minimal bold
- No gradients, no glassmorphism, no repeated stat cards

---

## 4. Routes

**Doctor** (desktop-first): `/doctor/login`, `/doctor/dashboard`, `/doctor/patients`, `/doctor/patients/new`, `/doctor/patients/:id`, `/doctor/patients/:id/medications`, `/doctor/alerts`, `/doctor/analytics`, `/doctor/qr-scanner`, `/doctor/profile`

**Patient** (mobile-first, 375–430px): `/patient/login`, `/patient/register`, `/patient/home`, `/patient/check-in`, `/patient/medicines`, `/patient/alerts`, `/patient/analytics`, `/patient/history`, `/patient/qr`, `/patient/profile`

---

## 5. API contract — hand this to Member 2 (Backend) and Member 3 (Database) as-is

This is what the frontend will call. Building the UI against these shapes now means backend can implement independently and swap in later with zero UI changes.

```
POST /auth/login          { email, password } → { token, user }
GET  /auth/me
POST /invitations         { patientId } → { code, expiresAt }
POST /invitations/verify  { code } → { patient }
GET  /patients
POST /patients             { name, age, gender, phone, email, condition, diagnosis, allergies, notes, caretaker: {name, relationship, phone} }
GET  /patients/:id
POST /checkins
GET  /checkins/patient/:id
POST /ai/analyze-checkin
GET  /patients/:id/medications
POST /patients/:id/medications
POST /medications/:id/taken
GET  /alerts
PUT  /alerts/:id/resolve
GET  /analytics/patient/:id
GET  /analytics/doctor
POST /qr/generate
POST /qr/verify
```

**Check-in request** (what frontend sends):
```json
{
  "patientId": "patient_id",
  "symptoms": [{ "name": "Chest Discomfort", "severity": "SEVERE" }],
  "duration": "SINCE_YESTERDAY",
  "overallFeeling": "NOT_GOOD",
  "medicationAdherence": "MISSED_ONE_DOSE",
  "notes": "Feeling more tired today."
}
```

**AI response** (what frontend renders — Member 4, match this exactly):
```json
{
  "riskLevel": "HIGH",
  "riskScore": 87,
  "reason": "Increasing chest discomfort and fatigue compared with previous check-ins.",
  "alertRecipient": ["DOCTOR", "CARETAKER"],
  "followUpAction": "Contact patient within 2 hours.",
  "recommendation": "Seek guidance from your healthcare provider."
}
```

If any of these shapes need to change, that's a conversation before anyone codes against them — changing a field name after the fact is what causes integration breakage on day 2.

---

## 6. Demo mode (so frontend is never blocked waiting on backend)

`.env`: `VITE_API_BASE_URL=`, `VITE_USE_MOCK_DATA=true`

While `true`, `mockService.js` does everything: 8 seeded patients (Rahul Sharma – high/87, Priya Nair – medium/62, Arjun Mehta – low/18, + 5 more varied), invitation codes, and the deterministic demo risk rule —

- Severe symptom, or Chest Discomfort, or Breathing Difficulty, or "Very Unwell" → **HIGH / 87**
- Moderate symptoms, or multiple missed doses → **MEDIUM / 62**
- Otherwise → **LOW / 18**

This logic lives only in `mockService.js` / `ai.api.js`, clearly marked as temporary, so swapping to real `POST /ai/analyze-checkin` is a one-line change, not a UI rewrite.

Shared state (Context) is what makes the "patient checks in high-risk → doctor dashboard shows the alert" moment work live in the demo, without a real backend.

---

## 7. Build order (time-boxed)

**Phase 1 — Foundation** (~30 min): scaffold Vite+React+Tailwind, router, layouts, mock service skeleton, demo data.

**Phase 2 — Doctor core** (~1.5h): Login → Dashboard → Patients → Add Patient → Invitation Success → Patient Profile → Alerts.

**Phase 3 — Patient core** (~1.5h): Login → Invitation entry → Home → Daily Check-in (multi-step) → AI result → Medicines.

**Phase 4 — Connect the wow flow** (~30 min): patient check-in → shared state → doctor dashboard/alerts update live. This is the single most important thing to get working — more valuable than any extra screen.

**Phase 5 — If time remains**: Analytics, QR flow, History, Profile polish.

I'll run the app and fix errors after each phase rather than at the end.

---

## 8. What this means for your teammates

- **Backend (Member 2)**: build against the endpoint list and JSON shapes in section 5. Frontend won't touch business logic or wait on you — flipping `VITE_USE_MOCK_DATA=false` is the entire integration step on my end.
- **Database (Member 3)**: entities the frontend expects map to Users, Doctors, Patients, Medications, Medication_Reminders, Checkins, Alerts, Medical_History, QR_Access — matches what's already in the team doc, no changes needed from what you've planned.
- **AI (Member 4)**: match the check-in request / AI response shapes in section 5 exactly (field names and enum values like `riskLevel`, `SEVERE`, `MISSED_ONE_DOSE`). That's the only coupling point.

Nobody needs to wait on anyone — same conclusion as the team doc: all four of us build in parallel, only integration (swapping mock → real API) has a dependency, and that dependency is one env var on my side.
