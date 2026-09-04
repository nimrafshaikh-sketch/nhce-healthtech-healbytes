import React, { useState, useEffect } from "react";
import { CheckCircle2, AlertTriangle, ShieldCheck, Stethoscope } from "lucide-react";
import Modal from "../ui/Modal";
import Input from "../ui/Input";
import Button from "../ui/Button";
import { verifyPrescriptionDocument } from "../../api/documents.api";

export default function PrescriptionVerificationModal({ open, onClose, document, onVerified }) {
  const [formData, setFormData] = useState({
    name: "",
    dosage: "",
    frequency: "twice_daily",
    instructions: "",
    start_date: new Date().toISOString().split("T")[0],
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (document && document.extracted_data) {
      const findings = document.extracted_data.clinical_findings || [];
      const candidate = findings.find((f) => f.entity_type === "CANDIDATE_PRESCRIPTION") || {};
      setFormData({
        name: candidate.drug_name || "Metformin",
        dosage: candidate.dosage || "500mg",
        frequency: candidate.frequency || "twice_daily",
        instructions: candidate.instructions || "Take with meals as directed",
        start_date: new Date().toISOString().split("T")[0],
      });
    }
  }, [document]);

  async function handleApprove(e) {
    e.preventDefault();
    if (!document) return;
    setLoading(true);
    setError(null);
    try {
      const res = await verifyPrescriptionDocument(document.id, formData);
      onClose();
      if (onVerified) onVerified(res);
    } catch (err) {
      setError(err.message || "Failed to approve prescription.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Doctor Verification: Extracted Prescription Order">
      <form onSubmit={handleApprove} className="space-y-4">
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900 space-y-1">
          <p className="font-bold flex items-center gap-1.5 text-amber-800">
            <AlertTriangle size={14} className="text-amber-600" />
            Human-in-the-Loop Clinical Verification Required
          </p>
          <p className="text-amber-700 leading-relaxed">
            Candidate medication extracted from "{document?.title}". Please review and verify dosage, frequency, and instructions before officially creating the active clinical prescription.
          </p>
        </div>

        {error && (
          <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-xs text-red-700">
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <Input
            label="Medication Name *"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            required
          />
          <Input
            label="Dosage / Strength *"
            value={formData.dosage}
            onChange={(e) => setFormData({ ...formData, dosage: e.target.value })}
            required
          />
        </div>

        <div className="space-y-1">
          <label className="text-xs font-semibold text-ink-700">Frequency Schedule *</label>
          <select
            value={formData.frequency}
            onChange={(e) => setFormData({ ...formData, frequency: e.target.value })}
            className="w-full rounded-xl border border-ink-200 bg-white px-3 py-2 text-sm text-ink-900 focus:border-brand-500 focus:outline-none"
          >
            <option value="once_daily">Once Daily</option>
            <option value="twice_daily">Twice Daily</option>
            <option value="three_times_daily">Three Times Daily</option>
            <option value="weekly">Weekly</option>
            <option value="as_needed">As Needed (PRN)</option>
          </select>
        </div>

        <Input
          label="Clinical Instructions"
          value={formData.instructions}
          onChange={(e) => setFormData({ ...formData, instructions: e.target.value })}
        />

        <Input
          label="Prescription Start Date"
          type="date"
          value={formData.start_date}
          onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
          required
        />

        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={loading} className="bg-emerald-600 hover:bg-emerald-700 text-white">
            <ShieldCheck size={16} className="mr-1.5" />
            Approve & Create Prescription
          </Button>
        </div>
      </form>
    </Modal>
  );
}
