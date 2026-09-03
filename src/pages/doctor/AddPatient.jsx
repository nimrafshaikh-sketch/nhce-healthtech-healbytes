import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Copy, RefreshCw, Share2, CheckCircle2 } from "lucide-react";
import Topbar from "../../components/layout/Topbar";
import Input from "../../components/ui/Input";
import Select from "../../components/ui/Select";
import Textarea from "../../components/ui/Textarea";
import Button from "../../components/ui/Button";
import { useData } from "../../context/DataContext";

const emptyForm = {
  name: "",
  age: "",
  gender: "Female",
  phone: "",
  email: "",
  condition: "",
  diagnosis: "",
  allergies: "",
  notes: "",
  caretaker: { name: "", relationship: "", phone: "" },
};

export default function AddPatient() {
  const { addPatient, regenerateInvitation } = useData();
  const navigate = useNavigate();
  const [form, setForm] = useState(emptyForm);
  const [submitting, setSubmitting] = useState(false);
  const [created, setCreated] = useState(null);
  const [copied, setCopied] = useState(false);

  function update(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }
  function updateCaretaker(field, value) {
    setForm((f) => ({ ...f, caretaker: { ...f.caretaker, [field]: value } }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setSubmitting(true);
    try {
      const patient = await addPatient(form);
      setCreated(patient);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(created.invitationCode);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // clipboard unavailable in this environment — silently ignore
    }
  }

  async function handleRegenerate() {
    const code = await regenerateInvitation(created.id);
    setCreated((c) => ({ ...c, invitationCode: code }));
  }

  if (created) {
    return (
      <>
        <Topbar title="Add Patient" subtitle="Patient onboarding" />
        <main className="flex flex-1 items-center justify-center px-6 py-10">
          <div className="w-full max-w-md rounded-2xl border border-ink-300/15 bg-white p-8 text-center shadow-raised">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-risk-low-bg text-risk-low">
              <CheckCircle2 size={26} />
            </div>
            <h1 className="mt-4 text-lg font-semibold text-ink-900">Patient Added Successfully</h1>
            <p className="mt-1 text-sm text-ink-500">{created.name} has been added to your patient list.</p>

            <div className="mt-6 rounded-2xl bg-canvas-soft p-5">
              <p className="text-xs uppercase tracking-wide text-ink-300">Invitation Code</p>
              <p className="mt-1 text-2xl font-bold tracking-widest text-brand-800">{created.invitationCode}</p>
              <div className="mt-4 flex flex-wrap items-center justify-center gap-2">
                <Button size="sm" variant="secondary" leftIcon={<Copy size={14} />} onClick={handleCopy}>
                  {copied ? "Copied" : "Copy"}
                </Button>
                <Button size="sm" variant="secondary" leftIcon={<RefreshCw size={14} />} onClick={handleRegenerate}>
                  Regenerate
                </Button>
                <Button size="sm" variant="secondary" leftIcon={<Share2 size={14} />} onClick={handleCopy}>
                  Share
                </Button>
              </div>
              <p className="mt-3 text-xs text-ink-400">Expires in 7 days</p>
            </div>

            <Button fullWidth size="lg" className="mt-6" onClick={() => navigate(`/doctor/patients/${created.id}`)}>
              Continue to Patient Profile
            </Button>
          </div>
        </main>
      </>
    );
  }

  return (
    <>
      <Topbar title="Add Patient" subtitle="Bring a new patient into HealBytes." />
      <main className="flex-1 px-6 py-6">
        <form onSubmit={handleSubmit} className="mx-auto max-w-2xl space-y-6">
          <section className="rounded-2xl border border-ink-300/15 bg-white p-6 shadow-card">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-ink-500">Patient Information</h2>
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              <Input label="Full Name" required value={form.name} onChange={(e) => update("name", e.target.value)} />
              <Input
                label="Age"
                type="number"
                required
                value={form.age}
                onChange={(e) => update("age", e.target.value)}
              />
              <Select label="Gender" value={form.gender} onChange={(e) => update("gender", e.target.value)}>
                <option>Female</option>
                <option>Male</option>
                <option>Other</option>
              </Select>
              <Input label="Phone" required value={form.phone} onChange={(e) => update("phone", e.target.value)} />
              <Input
                label="Email"
                type="email"
                required
                className="sm:col-span-2"
                value={form.email}
                onChange={(e) => update("email", e.target.value)}
              />
            </div>
          </section>

          <section className="rounded-2xl border border-ink-300/15 bg-white p-6 shadow-card">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-ink-500">Medical Information</h2>
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              <Input
                label="Primary Condition"
                required
                value={form.condition}
                onChange={(e) => update("condition", e.target.value)}
              />
              <Input
                label="Diagnosis"
                required
                value={form.diagnosis}
                onChange={(e) => update("diagnosis", e.target.value)}
              />
              <Input
                label="Allergies"
                placeholder="None known"
                value={form.allergies}
                onChange={(e) => update("allergies", e.target.value)}
              />
              <Textarea
                label="Important Notes"
                className="sm:col-span-2"
                value={form.notes}
                onChange={(e) => update("notes", e.target.value)}
              />
            </div>
          </section>

          <section className="rounded-2xl border border-ink-300/15 bg-white p-6 shadow-card">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-ink-500">Caretaker</h2>
            <div className="mt-4 grid gap-4 sm:grid-cols-3">
              <Input
                label="Name"
                required
                value={form.caretaker.name}
                onChange={(e) => updateCaretaker("name", e.target.value)}
              />
              <Input
                label="Relationship"
                required
                value={form.caretaker.relationship}
                onChange={(e) => updateCaretaker("relationship", e.target.value)}
              />
              <Input
                label="Phone"
                required
                value={form.caretaker.phone}
                onChange={(e) => updateCaretaker("phone", e.target.value)}
              />
            </div>
          </section>

          <div className="flex items-center justify-end gap-3 pb-6">
            <Button type="button" variant="secondary" onClick={() => navigate("/doctor/patients")}>
              Cancel
            </Button>
            <Button type="submit" loading={submitting}>
              Add Patient &amp; Generate Invitation
            </Button>
          </div>
        </form>
      </main>
    </>
  );
}
