import React, { createContext, useContext, useMemo, useReducer, useCallback, useEffect } from "react";
import { initialPatients, initialMedications, initialAlerts, initialCheckins, initialAppointments } from "../data/demoData";
import { createPatient as createPatientApi, getPatients as getPatientsApi, getMyPatientProfile } from "../api/patients.api";
import { redeemInvitation as redeemInvitationApi, generateInvitation as generateInvitationApi } from "../api/invitation.api";
import { submitCheckin as submitCheckinApi, waitForCheckinResult } from "../api/checkin.api";
import { analyzeCheckinAI } from "../api/ai.api";
import { resolveAlert as resolveAlertApi, getAlerts as getAlertsApi } from "../api/alerts.api";
import { addMedication as addMedicationApi, markMedicationStatus as markMedicationStatusApi, getMedications as getMedicationsApi } from "../api/medication.api";
import { getMyAppointments } from "../api/appointment.api";
import { generateId } from "../utils/id";
import { USE_MOCK } from "../api/client";
import { useAuth } from "./AuthContext";

const DataContext = createContext(null);

const initialState = {
  patients: initialPatients,
  medications: initialMedications,
  alerts: initialAlerts,
  checkins: initialCheckins,
  appointments: initialAppointments || [],
};

function reducer(state, action) {
  switch (action.type) {
    case "SYNC_STATE":
      return action.payload;
    case "SET_PATIENTS":
      return { ...state, patients: action.payload };
    case "SET_MEDICATIONS":
      return { ...state, medications: action.payload };
    case "SET_ALERTS":
      return { ...state, alerts: action.payload };
    case "SET_APPOINTMENTS":
      return { ...state, appointments: action.payload };
    case "ADD_PATIENT":
      return { ...state, patients: [action.payload, ...state.patients] };
    case "UPDATE_PATIENT":
      return {
        ...state,
        patients: state.patients.map((p) =>
          p.id === action.payload.id ? { ...p, ...action.payload.changes } : p
        ),
      };
    case "ADD_CHECKIN":
      return { ...state, checkins: [action.payload, ...state.checkins] };
    case "ADD_ALERT":
      return { ...state, alerts: [action.payload, ...state.alerts] };
    case "RESOLVE_ALERT":
      return {
        ...state,
        alerts: state.alerts.map((a) => (a.id === action.payload.id ? { ...a, status: "RESOLVED" } : a)),
      };
    case "ADD_MEDICATION":
      return { ...state, medications: [...state.medications, action.payload] };
    case "UPDATE_MEDICATION":
      return {
        ...state,
        medications: state.medications.map((m) =>
          m.id === action.payload.id ? { ...m, ...action.payload.changes } : m
        ),
      };
    default:
      return state;
  }
}

export function DataProvider({ children }) {
  const [state, dispatch] = useReducer(reducer, initialState, (init) => {
    try {
      const saved = localStorage.getItem("healbytes_data");
      if (saved) return JSON.parse(saved);
    } catch {
      // ignore
    }
    return init;
  });

  React.useEffect(() => {
    try {
      localStorage.setItem("healbytes_data", JSON.stringify(state));
    } catch {
      // ignore
    }
  }, [state]);

  React.useEffect(() => {
    const handleStorage = (e) => {
      if (e.key === "healbytes_data" && e.newValue) {
        try {
          dispatch({ type: "SYNC_STATE", payload: JSON.parse(e.newValue) });
        } catch {
          // ignore
        }
      }
    };
    window.addEventListener("storage", handleStorage);
    return () => window.removeEventListener("storage", handleStorage);
  }, []);

  // Live-mode data load. Previously `patients` (and everything derived from
  // it - the whole doctor dashboard, patient search, lab-tech patient names)
  // was seeded ONLY from hardcoded demo data (initialState above), even with
  // VITE_USE_MOCK_DATA=false - there was no live fetch anywhere. A doctor's
  // real patients (created via the receptionist or Add Patient flow) simply
  // never appeared. This fetches the real list once the doctor is
  // authenticated, and refreshData() lets any page force a reload after a
  // mutation the reducer doesn't already model locally (e.g. prescription
  // verification creating a Medication server-side).
  const { isAuthenticated, role, ready } = useAuth();

  const loadLiveData = useCallback(async () => {
    if (USE_MOCK || !ready || !isAuthenticated) return;
    if (role === "DOCTOR") {
      try {
        const patients = await getPatientsApi();
        dispatch({ type: "SET_PATIENTS", payload: patients });
      } catch {
        // Network/auth error - keep whatever's already in state rather than
        // wiping it; the page-level fetches will surface their own errors.
      }
      try {
        const medications = await getMedicationsApi();
        dispatch({ type: "SET_MEDICATIONS", payload: medications });
      } catch {
        // same as above
      }
      try {
        const alerts = await getAlertsApi();
        if (alerts) dispatch({ type: "SET_ALERTS", payload: alerts });
      } catch {
        // same as above
      }
      try {
        const appointments = await getMyAppointments();
        if (appointments) dispatch({ type: "SET_APPOINTMENTS", payload: appointments });
      } catch {
        // same as above
      }
    } else if (role === "PATIENT") {
      // Previously `state.patients` was only ever live-fetched for role
      // DOCTOR, so a patient logging in normally (not via fresh invitation
      // redemption) had no own Patient record in state at all -
      // getPatientById(user.id) fell through to the bare auth `user`
      // object, and the whole patient dashboard/profile silently rendered
      // undefined condition/riskLevel/caretaker/etc. Fetching the patient's
      // own profile here and seeding it into `patients` fixes that for
      // every page that reads it via getPatientById.
      try {
        const me = await getMyPatientProfile();
        if (me) dispatch({ type: "SET_PATIENTS", payload: [me] });
      } catch {
        // same as above - keep whatever's already in state
      }
      try {
        const medications = await getMedicationsApi();
        dispatch({ type: "SET_MEDICATIONS", payload: medications });
      } catch {
        // same as above
      }
    }
  }, [isAuthenticated, role, ready]);

  useEffect(() => {
    loadLiveData();
  }, [loadLiveData]);

  const addPatient = useCallback(async (formData) => {
    const patient = await createPatientApi(formData);
    dispatch({ type: "ADD_PATIENT", payload: patient });
    return patient;
  }, []);

  const redeemInvitationCode = useCallback(
    async (payload) => {
      return await redeemInvitationApi(payload, state.patients);
    },
    [state.patients]
  );

  const regenerateInvitation = useCallback(
    async (patientId) => {
      const { code } = await generateInvitationApi(patientId, state.patients);
      dispatch({ type: "UPDATE_PATIENT", payload: { id: patientId, changes: { invitationCode: code } } });
      return code;
    },
    [state.patients]
  );

  const submitCheckin = useCallback(
    async (patientId, payload) => {
      const fullPayload = { patientId, ...payload };
      // One POST, not two: previously this also called analyzeCheckinAI,
      // which in live mode hit the exact same /checkins/ endpoint a second
      // time and created a duplicate check-in row per submission. The real
      // AI verdict for a check-in isn't returned by the create call at all
      // (Django computes it afterward via Celery) - waitForCheckinResult
      // polls the same checkin back out until that verdict lands.
      const checkinBase = await submitCheckinApi(fullPayload);
      const aiResult = USE_MOCK
        ? await analyzeCheckinAI(fullPayload)
        : await waitForCheckinResult(checkinBase.id);
      const checkinRecord = { ...checkinBase, ...fullPayload, ...aiResult };

      dispatch({ type: "ADD_CHECKIN", payload: checkinRecord });
      dispatch({
        type: "UPDATE_PATIENT",
        payload: {
          id: patientId,
          changes: {
            riskLevel: aiResult.riskLevel,
            riskScore: aiResult.riskScore,
            reason: aiResult.reason,
            followUpAction: aiResult.followUpAction,
            recommendation: aiResult.recommendation,
            lastCheckIn: checkinRecord.date,
          },
        },
      });

      if (aiResult.riskLevel === "MEDIUM" || aiResult.riskLevel === "HIGH") {
        const patient = state.patients.find((p) => p.id === patientId);
        dispatch({
          type: "ADD_ALERT",
          payload: {
            id: generateId("alert"),
            patientId,
            patientName: patient?.name || "Patient",
            avatarInitials: patient?.avatarInitials || "PT",
            riskLevel: aiResult.riskLevel,
            riskScore: aiResult.riskScore,
            message: aiResult.reason,
            detectedAt: new Date(),
            status: "ACTIVE",
          },
        });
      }

      return aiResult;
    },
    [state.patients]
  );

  const resolveAlert = useCallback(async (alertId) => {
    await resolveAlertApi(alertId);
    dispatch({ type: "RESOLVE_ALERT", payload: { id: alertId } });
  }, []);

  // Local-only update for lightweight demo actions (e.g. scheduling a
  // follow-up) that don't yet have a dedicated backend endpoint.
  const updatePatient = useCallback((id, changes) => {
    dispatch({ type: "UPDATE_PATIENT", payload: { id, changes } });
  }, []);

  const addMedication = useCallback(async (patientId, formData) => {
    const medication = await addMedicationApi(patientId, formData);
    dispatch({ type: "ADD_MEDICATION", payload: medication });
    return medication;
  }, []);

  const markMedicationStatus = useCallback(
    async (medicationId, status) => {
      const result = await markMedicationStatusApi(medicationId, status);
      dispatch({ type: "UPDATE_MEDICATION", payload: { id: medicationId, changes: result } });

      // Roughly recompute adherence for the owning patient so the UI feels alive.
      const med = state.medications.find((m) => m.id === medicationId);
      if (med) {
        const patientMeds = state.medications.filter((m) => m.patientId === med.patientId);
        const taken = patientMeds.filter((m) => (m.id === medicationId ? status === "TAKEN" : m.status === "TAKEN")).length;
        const pct = patientMeds.length ? Math.round((taken / patientMeds.length) * 100) : 100;
        dispatch({ type: "UPDATE_PATIENT", payload: { id: med.patientId, changes: { medicationAdherencePct: pct } } });
      }
    },
    [state.medications]
  );

  // Loose (string-normalized) comparisons throughout: route params
  // (useParams()) are always strings, but live-mode ids from Django are
  // numbers - a strict === here would silently fail to find a real patient
  // by id even though it's right there in state.
  const getPatientById = useCallback(
    (id) => state.patients.find((p) => String(p.id) === String(id)),
    [state.patients]
  );
  const getMedicationsForPatient = useCallback(
    (id) => state.medications.filter((m) => String(m.patientId) === String(id)),
    [state.medications]
  );
  const getCheckinsForPatient = useCallback(
    (id) =>
      state.checkins
        .filter((c) => String(c.patientId) === String(id))
        .sort((a, b) => new Date(b.date) - new Date(a.date)),
    [state.checkins]
  );
  const getAlertsForPatient = useCallback(
    (id) => state.alerts.filter((a) => String(a.patientId) === String(id)),
    [state.alerts]
  );

  const activeAlertCount = useMemo(
    () => state.alerts.filter((a) => a.status === "ACTIVE").length,
    [state.alerts]
  );

  const value = {
    ...state,
    addPatient,
    refreshData: loadLiveData,
    redeemInvitationCode,
    verifyInvitationCode: redeemInvitationCode,
    regenerateInvitation,
    submitCheckin,
    resolveAlert,
    updatePatient,
    addMedication,
    markMedicationStatus,
    getPatientById,
    getMedicationsForPatient,
    getCheckinsForPatient,
    getAlertsForPatient,
    activeAlertCount,
  };

  return <DataContext.Provider value={value}>{children}</DataContext.Provider>;
}

export function useData() {
  const ctx = useContext(DataContext);
  if (!ctx) throw new Error("useData must be used within DataProvider");
  return ctx;
}
