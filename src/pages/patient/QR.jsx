import React, { useState, useEffect, useCallback } from "react";
import { RefreshCw, Clock } from "lucide-react";
import QRCard from "../../components/healthcare/QRCard";
import Button from "../../components/ui/Button";
import { useAuth } from "../../context/AuthContext";
import { generateQr } from "../../api/qr.api";

function secondsRemaining(expiresAt) {
  if (!expiresAt) return null;
  return Math.max(0, Math.round((new Date(expiresAt).getTime() - Date.now()) / 1000));
}

export default function PatientQR() {
  const { user } = useAuth();
  const [qr, setQr] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [remaining, setRemaining] = useState(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await generateQr(user.id);
      setQr(result);
      setRemaining(secondsRemaining(result.expires_at));
    } catch (err) {
      setError(err.message || "Failed to generate a consultation QR code.");
    } finally {
      setLoading(false);
    }
  }, [user.id]);

  // Generate a real token on mount - this is a consultation QR, not a
  // static/permanent code, so there is nothing valid to show until one is
  // actually requested from the backend.
  useEffect(() => {
    refresh();
  }, [refresh]);

  // Live 1-second countdown to the exact expiry, and auto-mark expired
  // client-side the moment it lapses (the backend is still the actual
  // authority - a doctor's scan of an expired token is rejected server-side
  // regardless of what this countdown shows).
  useEffect(() => {
    if (remaining === null) return;
    if (remaining <= 0) return;
    const id = setInterval(() => {
      setRemaining((prev) => (prev === null ? null : Math.max(0, prev - 1)));
    }, 1000);
    return () => clearInterval(id);
  }, [remaining !== null && remaining > 0]);

  const expired = remaining !== null && remaining <= 0;
  const minutes = remaining !== null ? Math.floor(remaining / 60) : null;
  const seconds = remaining !== null ? remaining % 60 : null;

  return (
    <div className="flex-1 px-5 pb-6 pt-8 text-center">
      <h1 className="text-lg font-semibold text-ink-900">Doctor Consultation QR</h1>
      <p className="mx-auto mt-1.5 max-w-xs text-sm text-ink-500">
        Show this to your doctor at your visit. It grants a single, time-limited consultation
        window and does not change your assigned doctor.
      </p>

      <div className="relative mt-6">
        <div className={expired ? "opacity-25" : ""}>
          <QRCard value={qr?.token || ""} />
        </div>
        {expired && (
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="rounded-full bg-ink-900/80 px-3 py-1 text-xs font-semibold text-white">
              Expired - generate a new code
            </span>
          </div>
        )}
      </div>

      {error && <p className="mt-4 text-xs text-risk-high">{error}</p>}

      {!error && remaining !== null && (
        <p className="mt-4 flex items-center justify-center gap-1.5 text-xs font-medium text-ink-500">
          <Clock size={13} />
          {expired ? "This code has expired." : `Expires in ${minutes}:${String(seconds).padStart(2, "0")}`}
        </p>
      )}
      <p className="mt-1 text-xs text-ink-300">Access is controlled, time-limited, and logged.</p>

      <Button
        variant="secondary"
        className="mt-5"
        leftIcon={<RefreshCw size={14} />}
        loading={loading}
        onClick={refresh}
      >
        Generate New Code
      </Button>
    </div>
  );
}
