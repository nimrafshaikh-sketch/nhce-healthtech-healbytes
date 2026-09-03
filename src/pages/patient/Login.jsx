import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { HeartPulse, ArrowRight } from "lucide-react";
import Input from "../../components/ui/Input";
import Button from "../../components/ui/Button";
import { useAuth } from "../../context/AuthContext";
import { useData } from "../../context/DataContext";

export default function PatientLogin() {
  const { login, status, error } = useAuth();
  const { patients } = useData();
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: patients[0]?.email || "", password: "demo1234" });

  async function handleSubmit(e) {
    e.preventDefault();
    await login("PATIENT", form);
    navigate("/patient/home");
  }

  return (
    <div className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-6 py-10">
      <div className="mb-8 flex items-center gap-2">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-700 text-white">
          <HeartPulse size={20} />
        </div>
        <span className="text-lg font-bold text-ink-900">HealBytes</span>
      </div>

      <h1 className="text-xl font-semibold text-ink-900">Welcome back</h1>
      <p className="mt-1 text-sm text-ink-500">Sign in to continue your care journey.</p>

      <form onSubmit={handleSubmit} className="mt-6 space-y-4">
        <Input
          label="Email or Phone"
          value={form.email}
          onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
        />
        <Input
          label="Password"
          type="password"
          value={form.password}
          onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
        />
        {error && <p className="text-sm text-risk-high">{error}</p>}
        <Button type="submit" fullWidth size="lg" loading={status === "loading"} rightIcon={<ArrowRight size={16} />}>
          Sign In
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-ink-500">
        New to HealBytes?{" "}
        <Link to="/patient/register" className="font-medium text-brand-700 hover:underline">
          Enter Invitation Code
        </Link>
      </p>
    </div>
  );
}
