import React, { createContext, useContext, useMemo, useReducer, useCallback, useEffect, useRef } from "react";
import { initialPatients, initialMedications, initialAlerts, initialCheckins, initialAppointments } from "../data/demoData";
import { createPatient as createPatientApi, getPatients as getPatientsApi, getMyPatientProfile } from "../api/patients.api";
import { redeemInvitation as redeemInvitationApi, generateInvitation as generateInvitationApi } from "../api/invitation.api";
import { submitCheckin as submitCheckinApi, getCheckins as getCheckinsApi, waitForCheckinResult } from "../api/checkin.api";
import { analyzeCheckinAI } from "../api/ai.api";
import { resolveAlert as resolveAlertApi, getAlerts as getAlertsApi } from "../api/alerts.api";
import { addMedication as addMedicationApi, markMedicationStatus as markMedicationStatusApi, getMedications as getMedicationsApi } from "../api/medication.api";
import { getMyAppointments } from "../api/appointment.api";
import { generateId } from "../utils/id";
import { DATA_STORAGE_KEY, USE_MOCK } from "../api/client";
import { useAuth } from "./AuthContext";

const CURRENT_MODE = USE_MOCK ? "mock" : "live";

const DataContext = createContext(null);

const mockInitialState = {
  patients: initialPatients,
  medications: initialMedications,
  alerts: initialAlerts,
  checkins: initialCheckins,
  appointments: initialAppointments || [],
};

const emptyState = {
  patients: [],
  medications: [],
  alerts: [],
  checkins: [],
  appointments: [],
};

const baseInitialState = USE_MOCK ? mockInitialState : emptyState;

function serializeScopedData(data, ownerUserId = null) {
  return JSON.stringify({
    mode: CURRENT_MODE,
    ownerUserId: ownerUserId ?? null,
    data,
  });
}

function parseScopedData(raw, expectedOwnerUserId = null) {
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object" || !parsed.data || parsed.mode !== CURRENT_MODE) {
      return null;
    }
    if (!USE_MOCK && parsed.ownerUserId !== (expectedOwnerUserId ?? null)) {
      return null;
    }
    const d = parsed.data;
    if (!Array.isArray(d.patients)) return null;
    return {
      patients: d.patients || [],
      medications: d.medications || [],
      alerts: d.alerts || [],
      checkins: d.checkins || [],
      appointments: d.appointments || [],
    };
  } catch {
    return null;
  }
}

function enrichPatientFromCheckin(patient, latestCheckin) {
  if (!patient || !latestCheckin) return patient;
  return {
    ...patient,
    riskLevel: latestCheckin.riskLevel || patient.riskLevel || null,
    riskScore: latestCheckin.riskScore !== undefined ? latestCheckin.riskScore : patient.riskScore ?? null,
    reason: latestCheckin.reason || patient.reason || "",
    followUpAction: latestCheckin.followUpAction || patient.followUpAction || "",
    recommendation: latestCheckin.recommendation || patient.recommendation || "",
    lastCheckIn: latestCheckin.date || patient.lastCheckIn || null,
  };
}

function reducer(state, action) {
  switch (action.type) {
    case "SYNC_STATE":
      return action.payload;
    case "SET_PATIENTS":
      return { ...state, patients: action.payload };
    case "SET_MEDICATIONS":
      return { ...state, medications: action.payload };
    case "SET_CHECKINS":
      return { ...state, checkins: action.payload };
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
          String(p.id) === String(action.payload.id) ? { ...p, ...action.payload.changes } : p
        ),
      };
    case "ADD_CHECKIN": {
      const next = state.checkins.filter((c) => String(c.id) !== String(action.payload.id));
      return { ...state, checkins: [action.payload, ...next] };
    }
    case "ADD_ALERT":
      return { ...state, alerts: [action.payload, ...state.alerts] };
    case "RESOLVE_ALERT":
      return {
        ...state,
        alerts: state.alerts.map((a) =>
          String(a.id) === String(action.payload.id) ? { ...a, status: "RESOLVED" } : a
        ),
      };
    case "ADD_MEDICATION":
      return { ...state, medications: [...state.medications, action.payload] };
    case "UPDATE_MEDICATION":
      return {
        ...state,
        medications: state.medications.map((m) =>
          String(m.id) === String(action.payload.id) ? { ...m, ...action.payload.changes } : m
        ),
      };
    default:
      return state;
  }
}

export function DataProvider({ children }) {
  const { isAuthenticated, role, user, ready } = useAuth();
  const ownerUserIdRef = useRef(user?.id ?? null);
  const lastOwnerKeyRef = useRef(null);
  ownerUserIdRef.current = user?.id ?? null;

  const [state, dispatch] = useReducer(reducer, baseInitialState, (init) => {
    if (!USE_MOCK) return init;
    const saved = parseScopedData(localStorage.getItem(DATA_STORAGE_KEY), null);
    return saved || init;
  });

  React.useEffect(() => {
    if (!ready) return;
    if (!USE_MOCK && !isAuthenticated) {
      try {
        localStorage.removeItem(DATA_STORAGE_KEY);
      } catch {
        // ignore
      }
      return;
    }
    try {
      localStorage.setItem(DATA_STORAGE_KEY, serializeScopedData(state, user?.id ?? null));
    } catch {
      // ignore
    }
  }, [state, ready, isAuthenticated, user?.id]);

  React.useEffect(() => {
    const handleStorage = (e) => {
      if (e.key === DATA_STORAGE_KEY && e.newValue) {
        const parsed = parseScopedData(e.newValue, ownerUserIdRef.current);
        if (parsed) dispatch({ type: "SYNC_STATE", payload: parsed });
      }
    };
    const handleAuthCleared = () => {
      lastOwnerKeyRef.current = null;
      dispatch({ type: "SYNC_STATE", payload: USE_MOCK ? mockInitialState : emptyState });
    };
    window.addEventListener("storage", handleStorage);
    window.addEventListener("healbytes:auth-cleared", handleAuthCleared);
    return () => {
      window.removeEventListener("storage", handleStorage);
      window.removeEventListener("healbytes:auth-cleared", handleAuthCleared);
    };
  }, []);

  const loadLiveData = useCallback(async () => {
    if (USE_MOCK || !ready || !isAuthenticated) return;
    if (role === "DOCTOR") {
      const [patientsRes, medsRes, checkinsRes, alertsRes, apptsRes] = await Promise.allSettled([
        getPatientsApi(),
        getMedicationsApi(),
        getCheckinsApi(),
        getAlertsApi(),
        getMyAppointments(),
      ]);

      const checkinsList =
        checkinsRes.status === "fulfilled" && Array.isArray(checkinsRes.value)
          ? [...checkinsRes.value].sort((a, b) => new Date(b.date) - new Date(a.date))
          : null;

      if (checkinsList) {
        dispatch({ type: "SET_CHECKINS", payload: checkinsList });
      }

      const latestByPatient = new Map();
      const checkinById = new Map();
      if (checkinsList) {
        for (const c of checkinsList) {
          checkinById.set(c.id, c);
          const key = String(c.patientId);
          if (!latestByPatient.has(key)) latestByPatient.set(key, c);
        }
      }

      if (patientsRes.status === "fulfilled" && Array.isArray(patientsRes.value)) {
        const enrichedPatients = patientsRes.value.map((p) =>
          enrichPatientFromCheckin(p, latestByPatient.get(String(p.id)))
        );
        dispatch({ type: "SET_PATIENTS", payload: enrichedPatients });
      }

      if (medsRes.status === "fulfilled" && Array.isArray(medsRes.value)) {
        dispatch({ type: "SET_MEDICATIONS", payload: medsRes.value });
      }

      if (alertsRes.status === "fulfilled" && Array.isArray(alertsRes.value)) {
        const enrichedAlerts = alertsRes.value.map((a) => ({
          ...a,
          riskScore: a.checkinId != null ? checkinById.get(a.checkinId)?.riskScore ?? null : a.riskScore,
        }));
        dispatch({ type: "SET_ALERTS", payload: enrichedAlerts });
      }

      if (apptsRes.status === "fulfilled" && Array.isArray(apptsRes.value)) {
        dispatch({ type: "SET_APPOINTMENTS", payload: apptsRes.value });
      }
    } else if (role === "PATIENT") {
      const [meRes, medsRes, checkinsRes, apptsRes] = await Promise.allSettled([
        getMyPatientProfile(),
        getMedicationsApi(),
        getCheckinsApi(),
        getMyAppointments(),
      ]);

      const checkinsList =
        checkinsRes.status === "fulfilled" && Array.isArray(checkinsRes.value)
          ? [...checkinsRes.value].sort((a, b) => new Date(b.date) - new Date(a.date))
          : null;

      if (checkinsList) {
        dispatch({ type: "SET_CHECKINS", payload: checkinsList });
      }

      if (meRes.status === "fulfilled" && meRes.value) {
        const enrichedMe = enrichPatientFromCheckin(meRes.value, checkinsList?.[0] || null);
        dispatch({ type: "SET_PATIENTS", payload: [enrichedMe] });
      }

      if (medsRes.status === "fulfilled" && Array.isArray(medsRes.value)) {
        dispatch({ type: "SET_MEDICATIONS", payload: medsRes.value });
      }

      if (apptsRes.status === "fulfilled" && Array.isArray(apptsRes.value)) {
        dispatch({ type: "SET_APPOINTMENTS", payload: apptsRes.value });
      }
    } else {
      dispatch({ type: "SYNC_STATE", payload: emptyState });
    }
  }, [isAuthenticated, role, ready]);

  useEffect(() => {
    if (!ready) return;
    if (USE_MOCK) return;
    const ownerKey = isAuthenticated ? `${role || ""}:${user?.id ?? ""}` : "anon";
    if (!isAuthenticated) {
      lastOwnerKeyRef.current = "anon";
      dispatch({ type: "SYNC_STATE", payload: emptyState });
      return;
    }
    if (lastOwnerKeyRef.current !== ownerKey) {
      lastOwnerKeyRef.current = ownerKey;
      const cached = parseScopedData(localStorage.getItem(DATA_STORAGE_KEY), user?.id ?? null);
      dispatch({ type: "SYNC_STATE", payload: cached || emptyState });
    }
    loadLiveData();
  }, [ready, isAuthenticated, role, user?.id, loadLiveData]);

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
      const matchedPatient =
        state.patients.find((p) => String(p.id) === String(patientId)) ||
        state.patients.find((p) => p.user != null && String(p.user) === String(patientId)) ||
        null;
      const resolvedPatientId = matchedPatient?.id ?? patientId;
      const fullPayload = { patientId: resolvedPatientId, ...payload };

      const checkinBase = await submitCheckinApi(fullPayload);
      const aiResult = USE_MOCK
        ? await analyzeCheckinAI(fullPayload)
        : await waitForCheckinResult(checkinBase.id);
      const checkinRecord = {
        ...checkinBase,
        ...fullPayload,
        ...aiResult,
        patientId: resolvedPatientId,
      };

      dispatch({ type: "ADD_CHECKIN", payload: checkinRecord });
      dispatch({
        type: "UPDATE_PATIENT",
        payload: {
          id: resolvedPatientId,
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

      // Live alerts are created exclusively by backend Celery workflows
      // (apps.alerts.tasks.route_alert_for_checkin). Never fabricate alerts locally.
      if (USE_MOCK && (aiResult.riskLevel === "MEDIUM" || aiResult.riskLevel === "HIGH")) {
        dispatch({
          type: "ADD_ALERT",
          payload: {
            id: generateId("alert"),
            patientId: resolvedPatientId,
            patientName: matchedPatient?.name || "Patient",
            avatarInitials: matchedPatient?.avatarInitials || "PT",
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
      const med = state.medications.find((m) => String(m.id) === String(medicationId));
      if (med) {
        const patientMeds = state.medications.filter((m) => String(m.patientId) === String(med.patientId));
        const taken = patientMeds.filter((m) => (String(m.id) === String(medicationId) ? status === "TAKEN" : m.status === "TAKEN")).length;
        const pct = patientMeds.length ? Math.round((taken / patientMeds.length) * 100) : 100;
        dispatch({ type: "UPDATE_PATIENT", payload: { id: med.patientId, changes: { medicationAdherencePct: pct } } });
      }
    },
    [state.medications]
  );

  const getPatientById = useCallback(
    (id) => (id == null ? null : state.patients.find((p) => String(p.id) === String(id)) || null),
    [state.patients]
  );
  const getPatientByUserId = useCallback(
    (userId) => {
      if (userId == null) return null;
      const byUser = state.patients.find((p) => p.user != null && String(p.user) === String(userId));
      if (byUser) return byUser;
      return USE_MOCK ? state.patients.find((p) => String(p.id) === String(userId)) || null : null;
    },
    [state.patients]
  );
  const currentPatient = useMemo(() => {
    if (role !== "PATIENT") return null;
    return getPatientByUserId(user?.id) || (!USE_MOCK ? state.patients[0] || null : null);
  }, [role, user?.id, getPatientByUserId, state.patients]);

  const getMedicationsForPatient = useCallback(
    (id) => (id == null ? [] : state.medications.filter((m) => String(m.patientId) === String(id))),
    [state.medications]
  );
  const getCheckinsForPatient = useCallback(
    (id) =>
      id == null
        ? []
        : state.checkins
            .filter((c) => String(c.patientId) === String(id))
            .sort((a, b) => new Date(b.date) - new Date(a.date)),
    [state.checkins]
  );
  const getAlertsForPatient = useCallback(
    (id) => (id == null ? [] : state.alerts.filter((a) => String(a.patientId) === String(id))),
    [state.alerts]
  );

  const activeAlertCount = useMemo(
    () => state.alerts.filter((a) => a.status === "ACTIVE").length,
    [state.alerts]
  );

  const value = {
    ...state,
    currentPatient,
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
    getPatientByUserId,
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
