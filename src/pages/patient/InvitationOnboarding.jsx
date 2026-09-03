import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { HeartPulse, CheckCircle2 } from "lucide-react";
import Input from "../../components/ui/Input";
import Button from "../../components/ui/Button";
import Avatar from "../../components/ui/Avatar";
import { useData } from "../../context/DataContext";
import { useAuth } from "../../context/AuthContext";

export default function InvitationOnboarding() {
  const { verifyInvitationCode } = useData();
  const { loginAsPatient } = useAuth();
  const navigate = useNavigate();
  const [code, setCode] = useState("");
  const [patient, setPatient] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  async function handleVerify(e) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const found = await verifyInvitationCode(code);
      setPatient(found);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function handleContinue() {
    loginAsPatient(patient);
    navigate("/patient/home");
  }

  if (patient) {
    return (
      <div className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-6 py-10 text-center">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-risk-low-bg text-risk-low">
          <CheckCircle2 size={26} />
        </div>
        <h1 className="mt-4 text-lg font-semibold text-ink-900">Invitation verified</h1>
        <p className="mt-1 text-sm text-ink-500">Confirm your details to finish setting up your account.</p>

        <div className="mt-6 flex flex-col items-center gap-2 rounded-2xl border border-ink-300/15 bg-white p-6 shadow-card">
          <Avatar name={patient.name} initials={patient.avatarInitials} size="lg" />
          <p className="text-base font-semibold text-ink-900">{patient.name}</p>
          <p className="text-sm text-ink-500">{patient.condition}</p>
          <p className="text-xs text-ink-300">Added by Dr. Sarah Chen</p>
        </div>

        <Button fullWidth size="lg" className="mt-6" onClick={handleContinue}>
          Continue to HealBytes
        </Button>
      </div>
    );
  }

  return (
    <div className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-6 py-10">
      <div className="mb-8 flex items-center gap-2">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-700 text-white">
          <HeartPulse size={20} />
        </div>
        <span className="text-lg font-bold text-ink-900">HealBytes</span>
      </div>

      <h1 className="text-xl font-semibold text-ink-900">Welcome to HealBytes</h1>
      <p className="mt-1 text-sm text-ink-500">Enter the invitation code provided by your healthcare provider.</p>

      <form onSubmit={handleVerify} className="mt-6 space-y-4">
        <Input
          label="Invitation Code"
          placeholder="HB-XXXXX"
          value={code}
          onChange={(e) => setCode(e.target.value.toUpperCase())}
          error={error}
          className="text-center text-lg tracking-widest"
        />
        <Button type="submit" fullWidth size="lg" loading={loading}>
          Verify Invitation
        </Button>
      </form>

      <p className="mt-6 text-center text-xs text-ink-400">Demo code: HB-7K29X</p>
    </div>
  );
}
