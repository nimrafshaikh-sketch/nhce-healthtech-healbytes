import React from "react";
import { useNavigate } from "react-router-dom";
import { User, Stethoscope, ArrowRight } from "lucide-react";

export default function RoleSelector() {
  const navigate = useNavigate();

  return (
    <section id="role-selector" className="bg-canvas py-16">
      <div className="mx-auto max-w-3xl px-6 lg:px-8 text-center">
        <h2 className="text-2xl font-bold text-ink-900 sm:text-3xl">How would you like to continue?</h2>
        <p className="mt-3 text-sm text-ink-500">Select your portal to access your account.</p>
        
        <div className="mt-10 grid gap-6 sm:grid-cols-2 text-left">
          <button
            onClick={() => navigate("/patient/login")}
            className="group relative flex flex-col rounded-2xl border border-ink-300/20 bg-white p-8 shadow-card transition hover:border-brand-300 hover:shadow-raised"
          >
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-brand-50 text-brand-700">
              <User size={24} />
            </div>
            <h3 className="mt-5 text-xl font-semibold text-ink-900">Patient</h3>
            <p className="mt-2 text-sm text-ink-500 flex-1">
              Access your care, medicines and daily check-ins.
            </p>
            <span className="mt-6 flex items-center gap-1.5 text-sm font-medium text-brand-700">
              Continue <ArrowRight size={16} className="transition-transform group-hover:translate-x-1" />
            </span>
          </button>

          <button
            onClick={() => navigate("/doctor/login")}
            className="group relative flex flex-col rounded-2xl border border-ink-300/20 bg-white p-8 shadow-card transition hover:border-brand-300 hover:shadow-raised"
          >
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-brand-50 text-brand-700">
              <Stethoscope size={24} />
            </div>
            <h3 className="mt-5 text-xl font-semibold text-ink-900">Doctor</h3>
            <p className="mt-2 text-sm text-ink-500 flex-1">
              Monitor patients, review risks and coordinate follow-up.
            </p>
            <span className="mt-6 flex items-center gap-1.5 text-sm font-medium text-brand-700">
              Continue <ArrowRight size={16} className="transition-transform group-hover:translate-x-1" />
            </span>
          </button>
        </div>
      </div>
    </section>
  );
}
