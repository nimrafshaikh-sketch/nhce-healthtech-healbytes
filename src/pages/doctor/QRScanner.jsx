import React, { useState, useRef, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import jsQR from "jsqr";
import { Camera, CameraOff, ScanLine, AlertTriangle, KeyRound } from "lucide-react";
import Topbar from "../../components/layout/Topbar";
import Input from "../../components/ui/Input";
import Button from "../../components/ui/Button";
import { useData } from "../../context/DataContext";
import { useAuth } from "../../context/AuthContext";
import { verifyQr } from "../../api/qr.api";
import ClinicalBriefCard from "../../components/doctor/ClinicalBriefCard";

// Scanner lifecycle states. The backend (apps.qr.views.QRVerifyView) is the
// sole authority on whether a token is valid/expired/tampered - this
// component only decodes the QR image and hands the raw string to the
// backend; it never makes an authorization decision on its own (Part 3/13).
const STATE = {
  IDLE: "idle",
  REQUESTING_PERMISSION: "requesting_permission",
  PERMISSION_DENIED: "permission_denied",
  CAMERA_UNAVAILABLE: "camera_unavailable",
  SCANNING: "scanning",
  VERIFYING: "verifying",
  ERROR: "error",
  SUCCESS: "success",
};

export default function QRScanner() {
  const { patients, medications, checkins } = useData();
  const { user } = useAuth();
  const navigate = useNavigate();

  const [state, setState] = useState(STATE.IDLE);
  const [errorMessage, setErrorMessage] = useState("");
  const [scanResult, setScanResult] = useState(null);
  const [manualToken, setManualToken] = useState("");

  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);
  const rafRef = useRef(null);
  const verifyingRef = useRef(false); // guards against decoding + firing multiple verify calls per frame loop

  const stopCamera = useCallback(() => {
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    rafRef.current = null;
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
  }, []);

  const handleDecodedToken = useCallback(
    async (token) => {
      if (verifyingRef.current) return;
      verifyingRef.current = true;
      stopCamera();
      setState(STATE.VERIFYING);
      try {
        const result = await verifyQr(token, patients, { medications, checkins });
        setScanResult(result);
        setState(STATE.SUCCESS);
      } catch (err) {
        setErrorMessage(err.message || "Invalid or expired QR code.");
        setState(STATE.ERROR);
      } finally {
        verifyingRef.current = false;
      }
    },
    [patients, medications, checkins, stopCamera]
  );

  const scanLoop = useCallback(() => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas || video.readyState !== video.HAVE_ENOUGH_DATA) {
      rafRef.current = requestAnimationFrame(scanLoop);
      return;
    }
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext("2d", { willReadFrequently: true });
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
    const code = jsQR(imageData.data, imageData.width, imageData.height, {
      inversionAttempts: "dontInvert",
    });
    if (code && code.data) {
      handleDecodedToken(code.data);
      return; // handleDecodedToken stops the camera; don't schedule another frame
    }
    rafRef.current = requestAnimationFrame(scanLoop);
  }, [handleDecodedToken]);

  const startCamera = useCallback(async () => {
    setErrorMessage("");
    setState(STATE.REQUESTING_PERMISSION);

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setState(STATE.CAMERA_UNAVAILABLE);
      setErrorMessage("This browser does not support camera access.");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "environment" },
        audio: false,
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      setState(STATE.SCANNING);
      rafRef.current = requestAnimationFrame(scanLoop);
    } catch (err) {
      if (err.name === "NotAllowedError" || err.name === "SecurityError") {
        setState(STATE.PERMISSION_DENIED);
        setErrorMessage("Camera access was denied. Allow camera access to scan a patient's QR code.");
      } else if (err.name === "NotFoundError" || err.name === "OverconstrainedError") {
        setState(STATE.CAMERA_UNAVAILABLE);
        setErrorMessage("No camera was found on this device.");
      } else {
        setState(STATE.CAMERA_UNAVAILABLE);
        setErrorMessage(err.message || "Unable to access the camera.");
      }
    }
  }, [scanLoop]);

  // Request camera permission as soon as the scanner opens (Part 3, step 1).
  useEffect(() => {
    startCamera();
    return () => stopCamera();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleManualSubmit(e) {
    e.preventDefault();
    if (!manualToken.trim()) return;
    handleDecodedToken(manualToken.trim());
  }

  function reset() {
    setScanResult(null);
    setErrorMessage("");
    setManualToken("");
    startCamera();
  }

  return (
    <>
      <Topbar title="Scan Patient QR" subtitle="Access secure, time-limited consultation history via QR." />
      <main className="flex-1 px-6 py-10">
        {state === STATE.SUCCESS && scanResult ? (
          <ClinicalBriefCard
            data={scanResult}
            isPrimaryDoctor={scanResult.patient.doctor === user?.id}
            onContinue={() => navigate(`/doctor/patients/${scanResult.patient.id}`)}
            onScanAnother={reset}
          />
        ) : (
          <div className="mx-auto max-w-md text-center">
            <div className="relative mx-auto flex h-64 w-64 items-center justify-center overflow-hidden rounded-3xl border-2 border-dashed border-brand-300 bg-brand-50 text-brand-600">
              {/* Video element stays mounted (even while showing an overlay) so
                  startCamera() always has a ref to attach the stream to. */}
              <video
                ref={videoRef}
                className={`h-full w-full object-cover ${state === STATE.SCANNING ? "block" : "hidden"}`}
                playsInline
                muted
              />
              <canvas ref={canvasRef} className="hidden" />

              {state === STATE.IDLE && <ScanLine size={48} />}
              {state === STATE.REQUESTING_PERMISSION && (
                <div className="flex flex-col items-center gap-2 px-4">
                  <Camera size={40} className="animate-pulse" />
                  <p className="text-sm font-medium">Camera access required</p>
                </div>
              )}
              {state === STATE.SCANNING && (
                <div className="pointer-events-none absolute inset-0 flex items-end justify-center pb-3">
                  <span className="rounded-full bg-ink-900/70 px-3 py-1 text-xs font-semibold text-white">
                    Scanning...
                  </span>
                </div>
              )}
              {state === STATE.VERIFYING && (
                <div className="flex flex-col items-center gap-2 px-4">
                  <ScanLine size={40} className="animate-pulse" />
                  <p className="text-sm font-medium">Verifying...</p>
                </div>
              )}
              {(state === STATE.PERMISSION_DENIED || state === STATE.CAMERA_UNAVAILABLE) && (
                <div className="flex flex-col items-center gap-2 px-4 text-center">
                  <CameraOff size={40} />
                  <p className="text-sm font-medium">
                    {state === STATE.PERMISSION_DENIED ? "Camera access required" : "Camera unavailable"}
                  </p>
                </div>
              )}
              {state === STATE.ERROR && (
                <div className="flex flex-col items-center gap-2 px-4 text-center">
                  <AlertTriangle size={40} className="text-risk-high" />
                  <p className="text-sm font-medium text-risk-high">Invalid or expired QR code</p>
                </div>
              )}
            </div>

            {errorMessage && <p className="mt-4 text-sm text-risk-high">{errorMessage}</p>}

            {(state === STATE.PERMISSION_DENIED || state === STATE.CAMERA_UNAVAILABLE || state === STATE.ERROR) && (
              <Button className="mt-4" leftIcon={<Camera size={16} />} onClick={reset}>
                Try Again
              </Button>
            )}

            {state === STATE.SCANNING && (
              <p className="mt-4 text-sm text-ink-500">Point the camera at the patient's Health QR code.</p>
            )}

            <div className="my-6 flex items-center gap-3">
              <div className="h-px flex-1 bg-ink-300/20" />
              <span className="text-xs text-ink-300">camera unavailable? paste the token</span>
              <div className="h-px flex-1 bg-ink-300/20" />
            </div>

            <form onSubmit={handleManualSubmit} className="flex gap-2">
              <Input
                placeholder="Paste QR token"
                value={manualToken}
                onChange={(e) => setManualToken(e.target.value)}
                className="text-center font-mono text-xs"
              />
              <Button type="submit" variant="secondary" leftIcon={<KeyRound size={14} />}>
                Verify
              </Button>
            </form>
          </div>
        )}
      </main>
    </>
  );
}
