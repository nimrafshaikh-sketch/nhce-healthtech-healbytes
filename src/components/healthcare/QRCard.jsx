import React from "react";
import { QRCodeSVG } from "qrcode.react";

// Renders a REAL, camera-scannable QR code encoding `value` (the signed
// short-lived consultation token from apps.qr - see api/qr.api.js). This
// used to be a fake hashed grid that only LOOKED like a QR code and could
// never actually be decoded by a scanner (Part 2/3 root cause) - replaced
// with a genuine QR encoder so the doctor's real camera scanner
// (pages/doctor/QRScanner.jsx) can decode it end to end.
export default function QRCard({ value = "healbytes", size = 224 }) {
  return (
    <div className="mx-auto flex w-56 items-center justify-center rounded-2xl border border-ink-300/15 bg-white p-4 shadow-card">
      <QRCodeSVG value={String(value)} size={size - 32} level="M" includeMargin={false} />
    </div>
  );
}
