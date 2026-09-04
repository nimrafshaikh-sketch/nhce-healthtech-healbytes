import React, { createContext, useContext, useMemo, useReducer, useCallback } from "react";
import { initialPatients, initialMedications, initialAlerts, initialCheckins } from "../data/demoData";
import { createPatient as createPatientApi } from "../api/patients.api";
import { redeemInvitation as redeemInvitationApi, generateInvitation as generateInvitationApi } from "../api/invitation.api";
import { submitCheckin as submitCheckinApi } from "../api/checkin.api";
import { analyzeCheckinAI } from "../api/ai.api";
import { resolveAlert as resolveAlertApi } from "../api/alerts.api";
import { addMedication as addMedicationApi, markMedicationStatus as markMedicationStatusApi } from "../api/medication.api";
import { generateId } from "../utils/id";

const DataContext = createContext(null);

const initialState = {
  patients: initialPatients,
  medications: initialMedications,
  alerts: initialAlerts,
  checkins: initialCheckins,
};

function reducer(state, action) {
  switch (action.type) {
    case "SYNC_STATE":
      return action.payload;
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
      const checkinBase = await submitCheckinApi(fullPayload);
      const aiResult = await analyzeCheckinAI(fullPayload);
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

  const getPatientById = useCallback((id) => state.patients.find((p) => p.id === id), [state.patients]);
  const getMedicationsForPatient = useCallback(
    (id) => state.medications.filter((m) => m.patientId === id),
    [state.medications]
  );
  const getCheckinsForPatient = useCallback(
    (id) => state.checkins.filter((c) => c.patientId === id).sort((a, b) => new Date(b.date) - new Date(a.date)),
    [state.checkins]
  );
  const getAlertsForPatient = useCallback(
    (id) => state.alerts.filter((a) => a.patientId === id),
    [state.alerts]
  );

  const activeAlertCount = useMemo(
    () => state.alerts.filter((a) => a.status === "ACTIVE").length,
    [state.alerts]
  );

  const value = {
    ...state,
    addPatient,
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
