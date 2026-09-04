import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { HeartPulse, CheckCircle2, UserPlus, KeyRound } from "lucide-react";
import Input from "../../components/ui/Input";
import Button from "../../components/ui/Button";
import { useData } from "../../context/DataContext";
import { useAuth } from "../../context/AuthContext";
import { getMyPatientProfile } from "../../api/patients.api";

export default function InvitationOnboarding() {
  const { redeemInvitationCode } = useData();
  const { loginAsPatient, updateCurrentUser } = useAuth();
  const navigate = useNavigate();

  const [formData, setFormData] = useState({
    code: "",
    email: "",
    username: "",
    password: "",
  });
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  function handleChange(field, value) {
    setFormData((prev) => ({ ...prev, [field]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await redeemInvitationCode(formData);

      // Root-cause fix (Part 1): the account must show the EXACT Patient
      // record the invitation resolved to server-side (res.patient_id) -
      // never a value fabricated from whatever the person just typed into
      // this form. Persist the id/token first (loginAsPatient), so the
      // follow-up authenticated fetch of the real profile has a token to
      // send; mock mode already returns the full matched patient inline.
      loginAsPatient({ id: res.patient_id, email: formData.email }, res.access);
      const realProfile = res.patient || (await getMyPatientProfile());
      if (realProfile) updateCurrentUser(realProfile);

      setSuccess(true);
      setTimeout(() => navigate("/patient/home"), 1000);
    } catch (err) {
      setError(err.message || "Failed to redeem invitation code.");
    } finally {
      setLoading(false);
    }
  }

  if (success) {
    return (
      <div className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-6 py-10 text-center">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-emerald-50 text-emerald-600">
          <CheckCircle2 size={32} />
        </div>
        <h1 className="mt-4 text-xl font-bold text-ink-900">Account Activated!</h1>
        <p className="mt-2 text-sm text-ink-500">
          Your account has been created and linked to your doctor. Redirecting to your dashboard...
        </p>
      </div>
    );
  }

  return (
    <div className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-6 py-10">
      <div className="mb-8 flex items-center gap-3">
        <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand-700 text-white shadow-md shadow-brand-700/20">
          <HeartPulse size={22} />
        </div>
        <div>
          <span className="text-xl font-bold text-ink-900">HealBytes</span>
          <p className="text-xs text-ink-400">Patient Onboarding</p>
        </div>
      </div>

      <div className="rounded-2xl border border-ink-100 bg-white p-6 shadow-card">
        <h1 className="text-lg font-bold text-ink-900">Activate Your Account</h1>
        <p className="mt-1 text-xs text-ink-500">
          Enter the invitation code provided by your clinic to set up your secure patient portal.
        </p>

        {error && (
          <div className="mt-4 rounded-xl border border-red-200 bg-red-50 p-3 text-xs text-red-700">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-5 space-y-3.5">
          <Input
            label="Invitation Code"
            placeholder="e.g. HB-7K29X"
            value={formData.code}
            onChange={(e) => handleChange("code", e.target.value.toUpperCase())}
            required
            className="text-center font-mono font-bold tracking-wider"
          />

          <Input
            label="Email Address"
            type="email"
            placeholder="you@example.com"
            value={formData.email}
            onChange={(e) => handleChange("email", e.target.value)}
            required
          />

          <Input
            label="Username"
            placeholder="Choose a username"
            value={formData.username}
            onChange={(e) => handleChange("username", e.target.value)}
            required
          />

          <Input
            label="Password"
            type="password"
            placeholder="Create a secure password"
            value={formData.password}
            onChange={(e) => handleChange("password", e.target.value)}
            required
          />

          <Button type="submit" fullWidth size="lg" loading={loading} className="mt-2">
            <UserPlus size={16} className="mr-2" />
            Activate Account
          </Button>
        </form>
      </div>

      <p className="mt-6 text-center text-xs text-ink-400">
        Already have an active account?{" "}
        <a href="/login" className="font-semibold text-brand-700 hover:underline">
          Sign In
        </a>
      </p>
    </div>
  );
}
