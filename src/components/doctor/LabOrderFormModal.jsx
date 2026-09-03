import React, { useState } from "react";
import Modal from "../ui/Modal";
import Button from "../ui/Button";
import { orderLabTest } from "../../api/lab.api";

const LAB_CATALOG = [
  "CBC (Complete Blood Count)",
  "Lipid Panel",
  "Blood Glucose (Fasting)",
  "HbA1c",
  "Liver Function Test (LFT)",
  "Kidney Function Test (KFT)",
  "Urinalysis",
  "Thyroid Panel (TSH, T3, T4)",
];

export default function LabOrderFormModal({ open, onClose, patientId, patientName, doctorId, doctorName }) {
  const [loading, setLoading] = useState(false);
  const [selectedTests, setSelectedTests] = useState([]);

  const toggleTest = (test) => {
    if (selectedTests.includes(test)) {
      setSelectedTests(selectedTests.filter(t => t !== test));
    } else {
      setSelectedTests([...selectedTests, test]);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (selectedTests.length === 0) {
      alert("Please select at least one lab test.");
      return;
    }
    setLoading(true);
    try {
      for (const test of selectedTests) {
        await orderLabTest({
          patientId,
          patientName,
          doctorId,
          doctorName,
          testType: test,
          expectedBy: "Tomorrow",
        });
      }
      alert("Lab tests ordered successfully!");
      onClose();
    } catch (err) {
      alert("Failed to order lab tests.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal open={open} onClose={onClose} title="Order Lab Tests">
      <form onSubmit={handleSubmit} className="space-y-6">
        <p className="text-sm text-ink-500">Select tests to send to the lab queue for {patientName}.</p>
        
        <div className="grid grid-cols-2 gap-3 max-h-80 overflow-y-auto">
          {LAB_CATALOG.map((test) => (
            <label key={test} className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition ${selectedTests.includes(test) ? 'bg-brand-50 border-brand-300' : 'bg-white border-ink-200 hover:bg-ink-50'}`}>
              <input
                type="checkbox"
                checked={selectedTests.includes(test)}
                onChange={() => toggleTest(test)}
                className="mt-0.5 rounded border-ink-300 text-brand-600 focus:ring-brand-600"
              />
              <span className="text-sm font-medium text-ink-900">{test}</span>
            </label>
          ))}
        </div>

        <div className="flex justify-end gap-3 pt-4 border-t border-ink-100">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={loading} disabled={selectedTests.length === 0}>
            Order Selected Labs
          </Button>
        </div>
      </form>
    </Modal>
  );
}
