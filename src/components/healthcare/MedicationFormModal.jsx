import React, { useState, useEffect } from "react";
import Modal from "../ui/Modal";
import Input from "../ui/Input";
import Select from "../ui/Select";
import Textarea from "../ui/Textarea";
import Button from "../ui/Button";

const empty = {
  name: "",
  dosage: "",
  frequency: "Once daily",
  timeOfDay: "MORNING",
  instructions: "",
  startDate: new Date().toISOString().split("T")[0],
  endDate: "",
  is_active: true,
};

export default function MedicationFormModal({ open, onClose, onSubmit, initialData = null }) {
  const [form, setForm] = useState(empty);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (initialData) {
      setForm({
        name: initialData.name || "",
        dosage: initialData.dosage || "",
        frequency: initialData.frequency ? initialData.frequency.replace("_", " ").replace(/\b\w/g, l => l.toUpperCase()) : "Once daily",
        timeOfDay: initialData.timeOfDay || "MORNING",
        instructions: initialData.instructions || "",
        startDate: initialData.startDate || initialData.start_date || new Date().toISOString().split("T")[0],
        endDate: initialData.endDate || initialData.end_date || "",
        is_active: initialData.is_active !== undefined ? initialData.is_active : true,
      });
    } else {
      setForm(empty);
    }
  }, [initialData, open]);

  function update(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  function setDurationDays(days) {
    const start = form.startDate ? new Date(form.startDate) : new Date();
    if (days === 0) {
      update("endDate", "");
      return;
    }
    const end = new Date(start);
    end.setDate(end.getDate() + days);
    update("endDate", end.toISOString().split("T")[0]);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setSubmitting(true);
    try {
      await onSubmit(form);
      setForm(empty);
      onClose();
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title={initialData ? "Edit Medication" : "Add Medication"}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <Input
          label="Medication Name"
          required
          placeholder="e.g. Paracetamol"
          value={form.name}
          onChange={(e) => update("name", e.target.value)}
        />
        <div className="grid grid-cols-2 gap-4">
          <Input
            label="Dosage"
            required
            placeholder="e.g. 650 mg"
            value={form.dosage}
            onChange={(e) => update("dosage", e.target.value)}
          />
          <Select label="Frequency" value={form.frequency} onChange={(e) => update("frequency", e.target.value)}>
            <option>Once daily</option>
            <option>Twice daily</option>
            <option>Three times daily</option>
            <option>Weekly</option>
            <option>As needed</option>
          </Select>
        </div>

        {/* Quick Duration Selector */}
        <div className="space-y-1.5">
          <label className="text-xs font-semibold text-ink-700">Course Duration Preset</label>
          <div className="flex flex-wrap gap-1.5">
            {[
              { label: "5 Days", days: 5 },
              { label: "7 Days", days: 7 },
              { label: "10 Days", days: 10 },
              { label: "14 Days", days: 14 },
              { label: "30 Days", days: 30 },
              { label: "Ongoing", days: 0 },
            ].map((p) => (
              <button
                key={p.label}
                type="button"
                onClick={() => setDurationDays(p.days)}
                className="text-xs font-medium px-2.5 py-1 rounded-lg border border-ink-200 bg-canvas-soft hover:border-brand-500 hover:text-brand-700 hover:bg-brand-50 transition"
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <Input
            label="Start Date"
            type="date"
            value={form.startDate}
            onChange={(e) => update("startDate", e.target.value)}
          />
          <Input
            label="End Date (Course Completion)"
            type="date"
            value={form.endDate}
            onChange={(e) => update("endDate", e.target.value)}
          />
        </div>

        <Textarea
          label="Instructions"
          placeholder="e.g. After breakfast with water"
          value={form.instructions}
          onChange={(e) => update("instructions", e.target.value)}
        />

        {initialData && (
          <div className="flex items-center gap-2 pt-1">
            <input
              type="checkbox"
              id="is_active_chk"
              checked={form.is_active}
              onChange={(e) => update("is_active", e.target.checked)}
              className="rounded border-ink-300 text-brand-600 focus:ring-brand-500"
            />
            <label htmlFor="is_active_chk" className="text-xs font-medium text-ink-800">
              Active Medication (uncheck to complete/stop this course)
            </label>
          </div>
        )}

        <div className="flex justify-end gap-2 pt-3 border-t border-ink-100">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={submitting}>
            {initialData ? "Save Changes" : "Add Medication"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
