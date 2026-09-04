import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { FlaskConical, ArrowRight } from "lucide-react";
import Input from "../../components/ui/Input";
import Button from "../../components/ui/Button";
import { useAuth } from "../../context/AuthContext";
import { USE_MOCK } from "../../api/client";

export default function LabLogin() {
  const { login, status, error } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    email: USE_MOCK ? "lab@healbytes.demo" : "labtech@healbytes.local",
    password: USE_MOCK ? "demo1234" : "LabTechPass123!",
  });

  async function handleSubmit(e) {
    e.preventDefault();
    try {
      await login("LAB_TECH", form);
      navigate("/lab/dashboard");
    } catch (err) {
      // Handled in AuthContext
    }
  }

  return (
    <div className="grid min-h-screen bg-canvas lg:grid-cols-2">
      <div className="hidden flex-col justify-between bg-purple-900 p-10 text-white lg:flex">
        <div className="flex items-center gap-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-white/10">
            <FlaskConical size={18} />
          </div>
          <span className="text-lg font-bold">HealBytes</span>
        </div>
        <div className="max-w-sm">
          <p className="text-2xl font-semibold leading-snug">
            Clinical Diagnostic Laboratory.
          </p>
          <p className="mt-3 text-sm text-purple-200">
            Process physician diagnostic test orders, claim specimens, and publish validated laboratory findings.
          </p>
        </div>
        <p className="text-xs text-purple-300">HealBytes — Diagnostic Lab</p>
      </div>

      <div className="flex items-center justify-center p-6 sm:p-10">
        <form onSubmit={handleSubmit} className="w-full max-w-sm">
          <div className="mb-8 flex items-center gap-2 lg:hidden">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-purple-700 text-white">
              <FlaskConical size={18} />
            </div>
            <span className="text-lg font-bold text-ink-900">HealBytes</span>
          </div>

          <h1 className="text-xl font-semibold text-ink-900">Laboratory Sign In</h1>
          <p className="mt-1 text-sm text-ink-500">Sign in with laboratory technician credentials.</p>

          <div className="mt-6 space-y-4">
            <Input
              label="Lab Tech Email"
              type="email"
              name="email"
              autoComplete="username"
              value={form.email}
              onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
              required
            />
            <Input
              label="Password"
              type="password"
              name="password"
              autoComplete="current-password"
              value={form.password}
              onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
              required
            />
          </div>

          {error && <p className="mt-3 text-sm text-risk-high">{error}</p>}

          <Button
            type="submit"
            fullWidth
            size="lg"
            className="mt-6 bg-purple-700 hover:bg-purple-800 text-white"
            loading={status === "loading"}
            rightIcon={<ArrowRight size={16} />}
          >
            Sign in to Lab Worklist
          </Button>

          <p className="mt-4 text-center text-xs text-ink-400">
            Lab technician credentials pre-filled for testing.
          </p>
        </form>
      </div>
    </div>
  );
}
