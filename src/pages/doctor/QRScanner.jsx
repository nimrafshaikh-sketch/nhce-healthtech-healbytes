import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { QrCode, ScanLine } from "lucide-react";
import Topbar from "../../components/layout/Topbar";
import Input from "../../components/ui/Input";
import Button from "../../components/ui/Button";
import { useData } from "../../context/DataContext";
import { verifyQr } from "../../api/qr.api";

export default function QRScanner() {
  const { patients } = useData();
  const navigate = useNavigate();
  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [notFound, setNotFound] = useState(false);

  async function handleSimulateScan() {
    setLoading(true);
    try {
      const demoPatient = patients[0];
      const { patient } = await verifyQr(`qr_${demoPatient.id}_demo`, patients);
      navigate(`/doctor/patients/${patient.id}`);
    } finally {
      setLoading(false);
    }
  }

  function handleManualLookup(e) {
    e.preventDefault();
    const match = patients.find((p) => p.invitationCode.toUpperCase() === code.trim().toUpperCase());
    if (match) {
      navigate(`/doctor/patients/${match.id}`);
    } else {
      setNotFound(true);
    }
  }

  return (
    <>
      <Topbar title="Scan Patient QR" subtitle="Access secure medical history via QR." />
      <main className="flex-1 px-6 py-10">
        <div className="mx-auto max-w-md text-center">
          <div className="mx-auto flex h-40 w-40 items-center justify-center rounded-3xl border-2 border-dashed border-brand-300 bg-brand-50 text-brand-600">
            <ScanLine size={48} />
          </div>
          <p className="mt-4 text-sm text-ink-500">Point the camera at a patient's Health QR code.</p>

          <Button className="mt-6" fullWidth loading={loading} leftIcon={<QrCode size={16} />} onClick={handleSimulateScan}>
            Simulate Scan
          </Button>

          <div className="my-6 flex items-center gap-3">
            <div className="h-px flex-1 bg-ink-300/20" />
            <span className="text-xs text-ink-300">or enter code manually</span>
            <div className="h-px flex-1 bg-ink-300/20" />
          </div>

          <form onSubmit={handleManualLookup} className="flex gap-2">
            <Input
              placeholder="HB-XXXXX"
              value={code}
              onChange={(e) => {
                setCode(e.target.value);
                setNotFound(false);
              }}
              className="text-center"
              error={notFound ? "No patient found for that code." : undefined}
            />
            <Button type="submit" variant="secondary">
              Look Up
            </Button>
          </form>
        </div>
      </main>
    </>
  );
}
