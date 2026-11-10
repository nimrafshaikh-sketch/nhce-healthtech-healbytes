import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { login as loginApi, fetchCurrentUser } from "../api/auth.api";
import {
  AUTH_STORAGE_KEY,
  USE_MOCK,
  clearStoredAuth,
  getStoredAuth,
  setStoredAuth,
  isJwtExpired,
  refreshAccessToken,
  decodeJwtPayload,
} from "../api/client";

const AuthContext = createContext(null);
const EMPTY_AUTH = { role: null, user: null, token: null, refreshToken: null };

export function AuthProvider({ children }) {
  const [auth, setAuth] = useState(EMPTY_AUTH);
  const [status, setStatus] = useState("idle"); // idle | loading | error
  const [error, setError] = useState(null);
  const [ready, setReady] = useState(false);

  const persist = useCallback((value) => {
    if (value && value.token) {
      const normalized = {
        role: value.role ? String(value.role).toUpperCase() : null,
        user: value.user || null,
        token: value.token,
        refreshToken: value.refreshToken || null,
      };
      setAuth(normalized);
      setStoredAuth(normalized);
    } else {
      setAuth(EMPTY_AUTH);
      clearStoredAuth();
    }
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function bootstrapSession() {
      const stored = getStoredAuth();
      if (!stored) {
        if (!cancelled) {
          setAuth(EMPTY_AUTH);
          setReady(true);
        }
        return;
      }

      if (USE_MOCK) {
        if (!cancelled) {
          setAuth({
            role: stored.role ? String(stored.role).toUpperCase() : null,
            user: stored.user || null,
            token: stored.token,
            refreshToken: stored.refreshToken || null,
          });
          setReady(true);
        }
        return;
      }

      // Live mode: verify token validity (and refresh if access JWT expired)
      let activeToken = stored.token;
      if (isJwtExpired(activeToken)) {
        const renewed = await refreshAccessToken();
        if (!renewed) {
          if (!cancelled) {
            setAuth(EMPTY_AUTH);
            setReady(true);
          }
          return;
        }
        activeToken = renewed;
      }

      try {
        const freshUser = await fetchCurrentUser(activeToken);
        const latestStored = getStoredAuth() || stored;
        const claims = decodeJwtPayload(activeToken);
        const canonicalRole = (freshUser?.role || claims?.role || latestStored.role || "").toUpperCase() || null;
        const mergedUser = freshUser
          ? { ...(latestStored.user || {}), ...freshUser, role: canonicalRole }
          : latestStored.user;
        const nextAuth = {
          role: canonicalRole,
          user: mergedUser,
          token: latestStored.token || activeToken,
          refreshToken: latestStored.refreshToken || null,
        };
        if (!cancelled) {
          setAuth(nextAuth);
          setStoredAuth(nextAuth);
          setReady(true);
        }
      } catch (err) {
        if (err?.status === 401 || err?.status === 403) {
          clearStoredAuth();
          if (!cancelled) {
            setAuth(EMPTY_AUTH);
            setReady(true);
          }
        } else {
          // Transient network/server issue: preserve valid non-expired token
          const latestStored = getStoredAuth() || stored;
          if (!cancelled) {
            setAuth({
              role: latestStored.role ? String(latestStored.role).toUpperCase() : null,
              user: latestStored.user || null,
              token: latestStored.token || activeToken,
              refreshToken: latestStored.refreshToken || null,
            });
            setReady(true);
          }
        }
      }
    }

    bootstrapSession();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const handleCleared = () => {
      setAuth(EMPTY_AUTH);
      setError(null);
    };
    const handleRefreshed = (e) => {
      if (e?.detail?.token) {
        setAuth((prev) => ({
          ...prev,
          token: e.detail.token,
          refreshToken: e.detail.refreshToken || prev.refreshToken,
        }));
      }
    };
    const handleStorage = (e) => {
      if (e.key === AUTH_STORAGE_KEY) {
        const next = getStoredAuth();
        if (next) {
          setAuth({
            role: next.role ? String(next.role).toUpperCase() : null,
            user: next.user || null,
            token: next.token,
            refreshToken: next.refreshToken || null,
          });
        } else {
          setAuth(EMPTY_AUTH);
        }
      }
    };

    window.addEventListener("healbytes:auth-cleared", handleCleared);
    window.addEventListener("healbytes:auth-refreshed", handleRefreshed);
    window.addEventListener("storage", handleStorage);
    return () => {
      window.removeEventListener("healbytes:auth-cleared", handleCleared);
      window.removeEventListener("healbytes:auth-refreshed", handleRefreshed);
      window.removeEventListener("storage", handleStorage);
    };
  }, []);

  const login = useCallback(
    async (role, credentials) => {
      setStatus("loading");
      setError(null);
      try {
        const { token, refreshToken, user } = await loginApi({ role, ...credentials });
        const effectiveRole = (user?.role || role)?.toUpperCase();
        if (role && effectiveRole && effectiveRole !== String(role).toUpperCase()) {
          clearStoredAuth();
          const roleErr = new Error(`This account belongs to role ${effectiveRole}, not ${String(role).toUpperCase()}.`);
          setError(roleErr.message);
          setStatus("error");
          throw roleErr;
        }
        persist({
          role: effectiveRole,
          user: user ? { ...user, role: effectiveRole } : user,
          token,
          refreshToken: refreshToken || null,
        });
        setStatus("idle");
        return { user, role: effectiveRole };
      } catch (err) {
        setError(err.message || "Unable to sign in.");
        setStatus("error");
        throw err;
      }
    },
    [persist]
  );

  // Used after invitation verification + registration
  const loginAsPatient = useCallback(
    (patientRecord, token = "demo-patient-token", refreshToken = null) => {
      persist({ role: "PATIENT", user: patientRecord, token, refreshToken });
    },
    [persist]
  );

  const updateCurrentUser = useCallback(
    (changes) => {
      setAuth((prev) => {
        const next = { ...prev, user: { ...prev.user, ...changes } };
        setStoredAuth(next);
        return next;
      });
    },
    []
  );

  const logout = useCallback(() => {
    setError(null);
    setStatus("idle");
    persist(EMPTY_AUTH);
  }, [persist]);

  const value = {
    role: auth.role,
    user: auth.user,
    token: auth.token,
    refreshToken: auth.refreshToken,
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
