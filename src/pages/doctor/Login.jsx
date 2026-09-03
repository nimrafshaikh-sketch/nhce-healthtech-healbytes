import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Stethoscope, ArrowRight } from "lucide-react";
import Input from "../../components/ui/Input";
import Button from "../../components/ui/Button";
import { useAuth } from "../../context/AuthContext";

export default function DoctorLogin() {
  const { login, status, error } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: "sarah.chen@healbytes.demo", password: "demo1234" });

  async function handleSubmit(e) {
    e.preventDefault();
    await login("DOCTOR", form);
    navigate("/doctor/dashboard");
  }

  return (
    <div className="grid min-h-screen bg-canvas lg:grid-cols-2">
      <div className="hidden flex-col justify-between bg-brand-800 p-10 text-white lg:flex">
        <div className="flex items-center gap-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-white/10">
            <Stethoscope size={18} />
          </div>
          <span className="text-lg font-bold">HealBytes</span>
        </div>
        <div className="max-w-sm">
          <p className="text-2xl font-semibold leading-snug">
            Autonomous healthcare coordination &amp; follow-up.
          </p>
          <p className="mt-3 text-sm text-brand-100">
            Daily check-ins, AI risk detection, and doctor–caretaker coordination — so recovery doesn't stop at
            discharge.
          </p>
        </div>
        <p className="text-xs text-brand-200">HealBytes — Hackathon Preview</p>
      </div>

      <div className="flex items-center justify-center p-6 sm:p-10">
        <form onSubmit={handleSubmit} className="w-full max-w-sm">
          <div className="mb-8 flex items-center gap-2 lg:hidden">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-700 text-white">
              <Stethoscope size={18} />
            </div>
            <span className="text-lg font-bold text-ink-900">HealBytes</span>
          </div>

          <h1 className="text-xl font-semibold text-ink-900">Welcome back, doctor</h1>
          <p className="mt-1 text-sm text-ink-500">Sign in to continue coordinating patient care.</p>

          <div className="mt-6 space-y-4">
            <Input
              label="Email"
              type="email"
              name="email"
              autoComplete="username"
              value={form.email}
              onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
            />
            <Input
              label="Password"
              type="password"
              name="password"
              autoComplete="current-password"
              value={form.password}
              onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
            />
          </div>

          {error && <p className="mt-3 text-sm text-risk-high">{error}</p>}

          <Button
            type="submit"
            fullWidth
            size="lg"
            className="mt-6"
            loading={status === "loading"}
            rightIcon={<ArrowRight size={16} />}
          >
            Sign in to Dashboard
          </Button>

          <p className="mt-4 text-center text-xs text-ink-400">
            Demo mode — credentials are pre-filled, just sign in.
          </p>
        </form>
      </div>
    </div>
  );
}
