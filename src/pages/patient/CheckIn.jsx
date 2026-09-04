import React, { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, ArrowRight, Sparkles, ShieldCheck, ShieldAlert, ShieldQuestion } from "lucide-react";
import Button from "../../components/ui/Button";
import Textarea from "../../components/ui/Textarea";
import {
  FEELING_OPTIONS,
  SYMPTOM_OPTIONS,
  SEVERITY_OPTIONS,
  DURATION_OPTIONS,
  ADHERENCE_OPTIONS,
} from "../../utils/constants";
import { useAuth } from "../../context/AuthContext";
import { useData } from "../../context/DataContext";

const RESULT_COPY = {
  LOW: {
    icon: ShieldCheck,
    tone: "text-risk-low bg-risk-low-bg",
    title: "Everything looks stable",
    body: "Your responses do not indicate an immediate concern. Your care team will continue monitoring your progress.",
  },
  MEDIUM: {
    icon: ShieldQuestion,
    tone: "text-risk-medium bg-risk-medium-bg",
    title: "We noticed something to monitor",
    body: "Your symptoms show a change from your recent check-ins. Your care team has been informed.",
  },
  HIGH: {
    icon: ShieldAlert,
    tone: "text-risk-high bg-risk-high-bg",
    title: "Your care team has been notified",
    body: "Your responses indicate symptoms that may require medical attention. Please follow the instructions from your healthcare provider.",
  },
};

export default function CheckIn() {
  const { user } = useAuth();
  const { submitCheckin } = useData();
  const navigate = useNavigate();

  const [phase, setPhase] = useState("form"); // form | analyzing | result
  const [stepIndex, setStepIndex] = useState(0);
  const [form, setForm] = useState({
    feeling: null,
    symptoms: [], // [{ name, severity }]
    duration: null,
    adherence: null,
    notes: "",
  });
  const [aiResult, setAiResult] = useState(null);
  const [submitError, setSubmitError] = useState(null);

  const steps = useMemo(
    () => (form.symptoms.length ? ["feeling", "symptoms", "severity", "duration", "adherence", "notes"] : ["feeling", "symptoms", "duration", "adherence", "notes"]),
    [form.symptoms.length]
  );
  const currentStep = steps[stepIndex];

  function toggleSymptom(name) {
    setForm((f) => {
      const exists = f.symptoms.find((s) => s.name === name);
      const symptoms = exists ? f.symptoms.filter((s) => s.name !== name) : [...f.symptoms, { name, severity: null }];
      return { ...f, symptoms };
    });
  }

  function setSeverity(name, severity) {
    setForm((f) => ({
      ...f,
      symptoms: f.symptoms.map((s) => (s.name === name ? { ...s, severity } : s)),
    }));
  }

  function canProceed() {
    if (currentStep === "feeling") return Boolean(form.feeling);
    if (currentStep === "symptoms") return true;
    if (currentStep === "severity") return form.symptoms.every((s) => s.severity);
    if (currentStep === "duration") return Boolean(form.duration);
    if (currentStep === "adherence") return Boolean(form.adherence);
    return true;
  }

  function goNext() {
    if (stepIndex < steps.length - 1) setStepIndex((i) => i + 1);
  }
  function goBack() {
    if (stepIndex === 0) {
      navigate("/patient/home");
    } else {
      setStepIndex((i) => i - 1);
    }
  }

  async function handleSubmit() {
    setPhase("analyzing");
    setSubmitError(null);
    const payload = {
      symptoms: form.symptoms.map((s) => ({ name: s.name, severity: s.severity })),
      duration: form.duration,
      overallFeeling: form.feeling,
      medicationAdherence: form.adherence,
      notes: form.notes,
    };
    try {
      const result = await submitCheckin(user.id, payload);
      setAiResult(result);
      setPhase("result");
    } catch (err) {
      // Previously uncaught: an error here (e.g. the "already checked in
      // today" 400 the backend returns for a duplicate same-day check-in)
      // left the UI stuck on the "Analyzing…" screen forever with only an
      // unhandled promise rejection in the console.
      setSubmitError(err.message || "Could not submit your check-in. Please try again.");
      setPhase("form");
    }
  }

  if (phase === "analyzing") {
    return (
      <div className="flex flex-1 flex-col items-center justify-center px-8 text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-brand-50 text-brand-600">
          <Sparkles size={28} className="animate-pulse" />
        </div>
        <p className="mt-5 text-base font-semibold text-ink-900">Analyzing your check-in</p>
        <p className="mt-1.5 max-w-xs text-sm text-ink-500">
          Looking for changes in your symptoms and health patterns…
        </p>
        <div className="mt-6 h-1.5 w-40 overflow-hidden rounded-full bg-ink-900/5">
          <div className="h-full w-1/2 animate-[pulse_1.4s_ease-in-out_infinite] rounded-full bg-brand-500" />
        </div>
      </div>
    );
  }

  if (phase === "result" && aiResult) {
    const copy = RESULT_COPY[aiResult.riskLevel] || RESULT_COPY.LOW;
    const Icon = copy.icon;
    return (
      <div className="flex flex-1 flex-col px-6 py-10">
        <div className="flex flex-1 flex-col items-center justify-center text-center">
          <div className={`flex h-16 w-16 items-center justify-center rounded-full ${copy.tone}`}>
            <Icon size={30} />
          </div>
          <h1 className="mt-5 text-lg font-semibold text-ink-900">{copy.title}</h1>
          <p className="mt-2 max-w-sm text-sm text-ink-600">{copy.body}</p>

          {aiResult.riskLevel !== "LOW" && (
            <div className="mt-5 w-full max-w-sm rounded-2xl border border-ink-300/15 bg-white p-4 text-left shadow-card">
              <p className="text-xs font-semibold uppercase tracking-wide text-ink-300">Recommended</p>
              <p className="mt-1 text-sm text-ink-800">{aiResult.recommendation}</p>
            </div>
          )}

          <p className="mt-6 text-xs text-ink-300">
            This is a risk assessment to support monitoring — not a medical diagnosis.
          </p>
        </div>

        <Button size="lg" fullWidth onClick={() => navigate("/patient/home")}>
          Back to Home
        </Button>
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col px-5 pb-6 pt-6">
      <div className="mb-6 flex items-center gap-3">
        <button onClick={goBack} aria-label="Back" className="rounded-full p-1.5 text-ink-500 hover:bg-canvas-soft">
          <ArrowLeft size={18} />
        </button>
        <div className="flex flex-1 gap-1.5">
          {steps.map((s, i) => (
            <div
              key={s}
              className={`h-1.5 flex-1 rounded-full ${i <= stepIndex ? "bg-brand-600" : "bg-ink-900/5"}`}
            />
          ))}
        </div>
      </div>

      <div className="flex-1">
        {currentStep === "feeling" && (
          <div>
            <h1 className="text-lg font-semibold text-ink-900">How are you feeling today?</h1>
            <div className="mt-5 space-y-2.5">
              {FEELING_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => setForm((f) => ({ ...f, feeling: opt.value }))}
                  className={`flex w-full items-center gap-3 rounded-2xl border p-4 text-left transition ${
                    form.feeling === opt.value
                      ? "border-brand-500 bg-brand-50"
                      : "border-ink-300/20 bg-white hover:border-brand-200"
                  }`}
                >
                  <span className="text-2xl">{opt.emoji}</span>
                  <span className="text-sm font-medium text-ink-900">{opt.label}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {currentStep === "symptoms" && (
          <div>
            <h1 className="text-lg font-semibold text-ink-900">Are you experiencing any symptoms?</h1>
            <p className="mt-1 text-sm text-ink-500">Select all that apply.</p>
            <div className="mt-5 flex flex-wrap gap-2">
              {SYMPTOM_OPTIONS.map((name) => {
                const active = form.symptoms.some((s) => s.name === name);
                return (
                  <button
                    key={name}
                    onClick={() => toggleSymptom(name)}
                    className={`rounded-full border px-4 py-2 text-sm font-medium transition ${
                      active
                        ? "border-brand-600 bg-brand-700 text-white"
                        : "border-ink-300/25 bg-white text-ink-700 hover:border-brand-200"
                    }`}
                  >
                    {name}
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {currentStep === "severity" && (
          <div>
            <h1 className="text-lg font-semibold text-ink-900">How severe are your symptoms?</h1>
            <div className="mt-5 space-y-5">
              {form.symptoms.map((s) => (
                <div key={s.name}>
                  <p className="text-sm font-medium text-ink-800">{s.name}</p>
                  <div className="mt-2 flex gap-2">
                    {SEVERITY_OPTIONS.map((opt) => (
                      <button
                        key={opt.value}
                        onClick={() => setSeverity(s.name, opt.value)}
                        className={`flex-1 rounded-xl border py-2.5 text-sm font-medium transition ${
                          s.severity === opt.value
                            ? "border-brand-600 bg-brand-700 text-white"
                            : "border-ink-300/25 bg-white text-ink-700 hover:border-brand-200"
                        }`}
                      >
                        {opt.label}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {currentStep === "duration" && (
          <div>
            <h1 className="text-lg font-semibold text-ink-900">How long have you felt this way?</h1>
            <div className="mt-5 space-y-2.5">
              {DURATION_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => setForm((f) => ({ ...f, duration: opt.value }))}
                  className={`w-full rounded-2xl border p-4 text-left text-sm font-medium transition ${
                    form.duration === opt.value
                      ? "border-brand-500 bg-brand-50 text-ink-900"
                      : "border-ink-300/20 bg-white text-ink-700 hover:border-brand-200"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
        )}

        {currentStep === "adherence" && (
          <div>
            <h1 className="text-lg font-semibold text-ink-900">Did you take your medicines as prescribed?</h1>
            <div className="mt-5 space-y-2.5">
              {ADHERENCE_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => setForm((f) => ({ ...f, adherence: opt.value }))}
                  className={`w-full rounded-2xl border p-4 text-left text-sm font-medium transition ${
                    form.adherence === opt.value
                      ? "border-brand-500 bg-brand-50 text-ink-900"
                      : "border-ink-300/20 bg-white text-ink-700 hover:border-brand-200"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
        )}

        {currentStep === "notes" && (
          <div>
            <h1 className="text-lg font-semibold text-ink-900">Anything else you'd like your care team to know?</h1>
            <p className="mt-1 text-sm text-ink-500">Optional</p>
            <Textarea
              className="mt-5"
              rows={5}
              placeholder="Type here…"
              value={form.notes}
              onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
            />
          </div>
        )}
      </div>

      <div className="mt-6">
        {submitError && (
          <p className="mb-3 rounded-xl border border-risk-high/30 bg-risk-high-bg px-3.5 py-2.5 text-sm text-risk-high">
            {submitError}
          </p>
        )}
        {currentStep === "notes" ? (
          <Button size="lg" fullWidth onClick={handleSubmit}>
            Analyze My Check-in
          </Button>
        ) : (
          <Button size="lg" fullWidth rightIcon={<ArrowRight size={16} />} disabled={!canProceed()} onClick={goNext}>
            Continue
          </Button>
        )}
      </div>
    </div>
  );
}
