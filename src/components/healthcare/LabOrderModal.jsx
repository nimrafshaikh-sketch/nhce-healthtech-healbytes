import React, { useState } from "react";
import Modal from "../ui/Modal";
import Select from "../ui/Select";
import Textarea from "../ui/Textarea";
import Button from "../ui/Button";

const LAB_TEST_OPTIONS = [
  { value: "CBC", label: "Complete Blood Count (CBC)" },
  { value: "BLOOD_GLUCOSE", label: "Blood Glucose" },
  { value: "LIPID_PROFILE", label: "Lipid Profile" },
  { value: "HBA1C", label: "HbA1c (Glycated Hemoglobin)" },
  { value: "KFT", label: "Kidney Function Test (KFT)" },
  { value: "LFT", label: "Liver Function Test (LFT)" },
  { value: "TFT", label: "Thyroid Function Test (TFT)" },
  { value: "URINALYSIS", label: "Urinalysis" },
];

export default function LabOrderModal({ open, onClose, onSubmit }) {
  const [testName, setTestName] = useState("CBC");
  const [priority, setPriority] = useState("routine");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setSubmitting(true);
    try {
      await onSubmit({ testName, priority, notes });
      setTestName("CBC");
      setPriority("routine");
      setNotes("");
      onClose();
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Order Laboratory Test">
      <form onSubmit={handleSubmit} className="space-y-4">
        <Select
          label="Test Type"
          value={testName}
          onChange={(e) => setTestName(e.target.value)}
        >
          {LAB_TEST_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </Select>

        <Select
          label="Priority"
          value={priority}
          onChange={(e) => setPriority(e.target.value)}
        >
          <option value="routine">Routine</option>
          <option value="urgent">Urgent</option>
        </Select>

        <Textarea
          label="Clinical Notes / Indications"
          placeholder="e.g. Patient reports persistent headaches; rule out secondary causes."
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
        />

        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={submitting}>
            Submit Lab Order
          </Button>
        </div>
      </form>
    </Modal>
  );
}
