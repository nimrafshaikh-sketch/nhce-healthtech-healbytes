import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { login as loginApi } from "../api/auth.api";

const AuthContext = createContext(null);
const STORAGE_KEY = "healbytes_auth";

export function AuthProvider({ children }) {
  const [auth, setAuth] = useState({ role: null, user: null, token: null });
  const [status, setStatus] = useState("idle"); // idle | loading | error
  const [error, setError] = useState(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) setAuth(JSON.parse(raw));
    } catch {
      // ignore corrupted storage
    }
    setReady(true);
  }, []);

  const persist = useCallback((value) => {
    setAuth(value);
    try {
      if (value.token) localStorage.setItem(STORAGE_KEY, JSON.stringify(value));
      else localStorage.removeItem(STORAGE_KEY);
    } catch {
      // storage unavailable, continue in-memory
    }
  }, []);

  const login = useCallback(
    async (role, credentials) => {
      setStatus("loading");
      setError(null);
      try {
        const { token, user } = await loginApi({ role, ...credentials });
        persist({ role, user, token });
        setStatus("idle");
        return user;
      } catch (err) {
        setError(err.message || "Unable to sign in.");
        setStatus("error");
        throw err;
      }
    },
    [persist]
  );

  // Used after invitation verification + registration — no password step in demo mode.
  const loginAsPatient = useCallback(
    (patientRecord) => {
      persist({ role: "PATIENT", user: patientRecord, token: "demo-patient-token" });
    },
    [persist]
  );

  const updateCurrentUser = useCallback(
    (changes) => {
      setAuth((prev) => {
        const next = { ...prev, user: { ...prev.user, ...changes } };
        try {
          localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
        } catch {
          // ignore
        }
        return next;
      });
    },
    []
  );

  const logout = useCallback(() => {
    persist({ role: null, user: null, token: null });
  }, [persist]);

  const value = {
    role: auth.role,
    user: auth.user,
    token: auth.token,
    isAuthenticated: Boolean(auth.token),
    status,
    error,
    ready,
    login,
    loginAsPatient,
    updateCurrentUser,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
