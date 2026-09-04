import React, { useState } from "react";
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
};

export default function MedicationFormModal({ open, onClose, onSubmit }) {
  const [form, setForm] = useState(empty);
  const [submitting, setSubmitting] = useState(false);

  function update(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
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
    <Modal open={open} onClose={onClose} title="Add Medication">
      <form onSubmit={handleSubmit} className="space-y-4">
        <Input label="Medication Name" required value={form.name} onChange={(e) => update("name", e.target.value)} />
        <div className="grid grid-cols-2 gap-4">
          <Input
            label="Dosage"
            required
            placeholder="e.g. 500 mg"
            value={form.dosage}
            onChange={(e) => update("dosage", e.target.value)}
          />
          <Select label="Frequency" value={form.frequency} onChange={(e) => update("frequency", e.target.value)}>
            <option>Once daily</option>
            <option>Twice daily</option>
            <option>Three times daily</option>
            <option>As needed</option>
          </Select>
        </div>
        <Select label="Time" value={form.timeOfDay} onChange={(e) => update("timeOfDay", e.target.value)}>
          <option value="MORNING">Morning</option>
          <option value="AFTERNOON">Afternoon</option>
          <option value="EVENING">Evening</option>
        </Select>
        <div className="grid grid-cols-2 gap-4">
          <Input
            label="Start Date"
            type="date"
            value={form.startDate}
            onChange={(e) => update("startDate", e.target.value)}
          />
          <Input label="End Date" type="date" value={form.endDate} onChange={(e) => update("endDate", e.target.value)} />
        </div>
        <Textarea
          label="Instructions"
          placeholder="e.g. After breakfast"
          value={form.instructions}
          onChange={(e) => update("instructions", e.target.value)}
        />

        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={submitting}>
            Add Medication
          </Button>
        </div>
      </form>
    </Modal>
  );
}
