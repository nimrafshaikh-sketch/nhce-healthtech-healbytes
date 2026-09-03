import React, { useState } from "react";
import { RefreshCw } from "lucide-react";
import QRCard from "../../components/healthcare/QRCard";
import Button from "../../components/ui/Button";
import { useAuth } from "../../context/AuthContext";
import { generateQr } from "../../api/qr.api";
import { formatDateTime } from "../../utils/dateUtils";

export default function PatientQR() {
  const { user } = useAuth();
  const [qr, setQr] = useState({ token: `qr_${user.id}_seed`, updatedAt: new Date() });
  const [loading, setLoading] = useState(false);

  async function handleRefresh() {
    setLoading(true);
    try {
      const result = await generateQr(user.id);
      setQr(result);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex-1 px-5 pb-6 pt-8 text-center">
      <h1 className="text-lg font-semibold text-ink-900">My Health QR</h1>
      <p className="mx-auto mt-1.5 max-w-xs text-sm text-ink-500">
        Your healthcare provider can scan this QR to securely access your medical information.
      </p>

      <div className="mt-6">
        <QRCard value={qr.token} />
      </div>

      <p className="mt-4 text-xs text-ink-400">Last updated: {formatDateTime(qr.updatedAt)}</p>
      <p className="mt-1 text-xs text-ink-300">Access is controlled and logged.</p>

      <Button
        variant="secondary"
        className="mt-5"
        leftIcon={<RefreshCw size={14} />}
        loading={loading}
        onClick={handleRefresh}
      >
        Refresh Secure QR
      </Button>
    </div>
  );
}
