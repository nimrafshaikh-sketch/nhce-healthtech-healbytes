import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, Copy, CheckCircle2, KeyRound } from "lucide-react";
import { createReceptionistPatient, getDoctorsList, generatePatientInvitation } from "../../api/receptionist.api";

// Rewritten from a duplicate, disconnected implementation (previously used
// api/reception.api.js: hardcoded "doc_1"/"Dr. Sarah Chen", raw mock field
// names like `name`/`age`, and never generated an invitation code at all -
// it silently auto-booked an appointment instead). That was a second,
// broken "create patient" path alongside the correct one already working
// on the Receptionist Dashboard (api/receptionist.api.js). Per the "no
// duplicate systems" requirement, this page now reuses that same correct
// API module - same Django field names (full_name, date_of_birth,
// phone_number, doctor id), same real doctor list, and it now actually
// generates the invitation code this patient needs (Part 1: the code must
// bind to the exact Patient record just created, via patient_id - not name).
export default function NewPatient() {
  const navigate = useNavigate();
  const [doctors, setDoctors] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [created, setCreated] = useState(null);
  const [invitationCode, setInvitationCode] = useState(null);
  const [copied, setCopied] = useState(false);
  const [formData, setFormData] = useState({
    doctor: "",
    full_name: "",
    date_of_birth: "",
    gender: "MALE",
    phone_number: "",
    address: "",
    caretaker_name: "",
    caretaker_relationship: "",
    caretaker_phone_number: "",
    caretaker_email: "",
  });

  useEffect(() => {
    getDoctorsList()
      .then((res) => {
        const list = Array.isArray(res) ? res : res.results || [];
        setDoctors(list);
        if (list.length > 0) setFormData((f) => ({ ...f, doctor: list[0].id }));
      })
      .catch((err) => console.error("Failed to load doctors", err));
  }, []);

  const handleChange = (e) => {
    setFormData((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const patient = await createReceptionistPatient(formData);
      setCreated(patient);
      const invite = await generatePatientInvitation(patient.id);
      setInvitationCode(invite.code);
    } catch (err) {
      setError(err.message || "Error creating patient record.");
    } finally {
      setLoading(false);
    }
  };

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(invitationCode);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // clipboard unavailable in this environment - silently ignore
    }
  }

  if (created) {
    return (
      <div className="mx-auto max-w-md space-y-6 p-8">
        <div className="rounded-2xl border border-ink-200 bg-white p-8 text-center shadow-card">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-emerald-50 text-emerald-600">
            <CheckCircle2 size={26} />
          </div>
          <h1 className="mt-4 text-lg font-semibold text-ink-900">Patient Registered</h1>
          <p className="mt-1 text-sm text-ink-500">
            {created.full_name} (Patient #{created.id}) has been added, assigned to{" "}
            {doctors.find((d) => String(d.id) === String(formData.doctor))
              ? `Dr. ${doctors.find((d) => String(d.id) === String(formData.doctor)).first_name} ${
                  doctors.find((d) => String(d.id) === String(formData.doctor)).last_name
                }`
              : "the selected doctor"}
            .
          </p>

          <div className="mt-6 rounded-2xl bg-canvas-soft p-5">
            <p className="text-xs uppercase tracking-wide text-ink-300">Invitation Code</p>
            <p className="mt-1 text-2xl font-bold tracking-widest text-brand-800">
              {invitationCode || "Generating..."}
            </p>
            <p className="mt-2 text-xs text-ink-400">
              This code resolves only to Patient #{created.id} - give it to the patient to activate their account.
            </p>
            <button
              onClick={handleCopy}
              className="mt-4 inline-flex items-center gap-1.5 rounded-lg bg-white px-3 py-1.5 text-xs font-semibold text-ink-700 shadow-sm hover:bg-ink-50"
            >
              <Copy size={14} /> {copied ? "Copied" : "Copy Code"}
            </button>
          </div>

          <button
            onClick={() => navigate("/receptionist/dashboard")}
            className="mt-6 w-full rounded-xl bg-brand-600 py-2.5 text-sm font-medium text-white hover:bg-brand-700"
          >
            Back to Dashboard
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-3xl mx-auto space-y-8">
      <button
        onClick={() => navigate(-1)}
        className="flex items-center gap-2 text-ink-500 hover:text-ink-900 transition-colors"
      >
        <ArrowLeft size={18} />
        Back to Dashboard
      </button>

      <div>
        <h1 className="text-2xl font-bold text-ink-900">Register New Patient</h1>
        <p className="text-ink-500">Enter demographic details to create a new record and generate their invitation code.</p>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-ink-200 p-6">
        <form onSubmit={handleSubmit} className="space-y-6">
          {error && (
            <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-xs text-red-700">{error}</div>
          )}

          <div>
            <label className="block text-sm font-medium text-ink-700 mb-1">Assigned Primary Doctor</label>
            <select
              name="doctor"
              required
              value={formData.doctor}
              onChange={handleChange}
              className="w-full p-2.5 border border-ink-300 rounded-lg outline-none focus:border-brand-500 bg-white"
            >
              {doctors.map((doc) => (
                <option key={doc.id} value={doc.id}>
                  Dr. {doc.first_name} {doc.last_name} ({doc.specialization || "General Practice"})
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-ink-700 mb-1">Full Name</label>
              <input required name="full_name" value={formData.full_name} onChange={handleChange} type="text" className="w-full p-2.5 border border-ink-300 rounded-lg outline-none focus:border-brand-500" />
            </div>
            <div>
              <label className="block text-sm font-medium text-ink-700 mb-1">Phone Number</label>
              <input required name="phone_number" value={formData.phone_number} onChange={handleChange} type="tel" className="w-full p-2.5 border border-ink-300 rounded-lg outline-none focus:border-brand-500" />
            </div>
            <div>
              <label className="block text-sm font-medium text-ink-700 mb-1">Date of Birth</label>
              <input required name="date_of_birth" value={formData.date_of_birth} onChange={handleChange} type="date" className="w-full p-2.5 border border-ink-300 rounded-lg outline-none focus:border-brand-500" />
            </div>
            <div>
              <label className="block text-sm font-medium text-ink-700 mb-1">Gender</label>
              <select name="gender" value={formData.gender} onChange={handleChange} className="w-full p-2.5 border border-ink-300 rounded-lg outline-none focus:border-brand-500 bg-white">
                <option value="MALE">Male</option>
                <option value="FEMALE">Female</option>
                <option value="OTHER">Other</option>
              </select>
            </div>
            <div className="col-span-2">
              <label className="block text-sm font-medium text-ink-700 mb-1">Residential Address</label>
              <input name="address" value={formData.address} onChange={handleChange} type="text" className="w-full p-2.5 border border-ink-300 rounded-lg outline-none focus:border-brand-500" />
            </div>
          </div>

          <div className="border-t border-ink-100 pt-4">
            <p className="text-sm font-bold text-ink-700 mb-3">Caretaker / Emergency Contact (Optional)</p>
            <div className="grid grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-ink-700 mb-1">Caretaker Name</label>
                <input name="caretaker_name" value={formData.caretaker_name} onChange={handleChange} type="text" className="w-full p-2.5 border border-ink-300 rounded-lg outline-none focus:border-brand-500" />
              </div>
              <div>
                <label className="block text-sm font-medium text-ink-700 mb-1">Relationship</label>
                <input name="caretaker_relationship" value={formData.caretaker_relationship} onChange={handleChange} type="text" className="w-full p-2.5 border border-ink-300 rounded-lg outline-none focus:border-brand-500" />
              </div>
              <div>
                <label className="block text-sm font-medium text-ink-700 mb-1">Caretaker Phone</label>
                <input name="caretaker_phone_number" value={formData.caretaker_phone_number} onChange={handleChange} type="tel" className="w-full p-2.5 border border-ink-300 rounded-lg outline-none focus:border-brand-500" />
              </div>
              <div>
                <label className="block text-sm font-medium text-ink-700 mb-1">Caretaker Email</label>
                <input name="caretaker_email" value={formData.caretaker_email} onChange={handleChange} type="email" className="w-full p-2.5 border border-ink-300 rounded-lg outline-none focus:border-brand-500" />
              </div>
            </div>
          </div>

          <div className="pt-4 flex justify-end">
            <button
              type="submit"
              disabled={loading}
              className="flex items-center gap-2 bg-brand-600 text-white px-6 py-2.5 rounded-lg font-medium hover:bg-brand-700 disabled:opacity-50"
            >
              <KeyRound size={16} />
              {loading ? "Registering..." : "Create Patient & Generate Invitation"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
