import React, { useState } from "react";
import Modal from "../ui/Modal";
import Input from "../ui/Input";
import Button from "../ui/Button";
import { createPrescription } from "../../api/prescription.api";

// This modal previously also offered an "Upload written prescription -
// AI will extract the details automatically" image button that called a
// nonexistent `/prescriptions/upload` endpoint (mock mode faked a canned
// "Amoxicillin" result) and, worse, fed straight into medications state
// with NO doctor verification step before submission - a second,
// duplicate, and less safe OCR path alongside the real one (Upload
// Document -> OCR -> REVIEW_REQUIRED -> PrescriptionVerificationModal ->
// Medication, in components/healthcare/DocumentUploadModal.jsx +
// PrescriptionVerificationModal.jsx, already wired on the Patient Profile
// page and confirmed working end to end). Removed here rather than fixed,
// since the real path already covers this exact use case correctly
// (Part 11: OCR output must remain candidate data until doctor
// verification - this shortcut violated that).
export default function PrescriptionFormModal({ open, onClose, patientId }) {
  const [loading, setLoading] = useState(false);
  const [medications, setMedications] = useState([
    { name: "", dosage: "", frequency: "", duration: "", instructions: "" }
  ]);

  const handleAddRow = () => {
    setMedications([...medications, { name: "", dosage: "", frequency: "", duration: "", instructions: "" }]);
  };

  const handleMedChange = (index, field, value) => {
    const newMeds = [...medications];
    newMeds[index][field] = value;
    setMedications(newMeds);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const validMeds = medications.filter(m => m.name && m.dosage);
      if (validMeds.length === 0) {
        alert("Please add at least one medication with a name and dosage.");
        setLoading(false);
        return;
      }
      await createPrescription({
        patientId,
        medications: validMeds,
      });
      alert("Prescription created successfully!");
      onClose();
    } catch (err) {
      alert(err.message || "Failed to create prescription.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal open={open} onClose={onClose} title="Create Prescription">
      <div className="space-y-6">
        <p className="text-xs text-ink-400">
          For a scanned/photographed prescription, use "Upload Document" on the patient's Documents
          tab instead - it runs OCR and requires your verification before creating a medication.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="max-h-96 overflow-y-auto space-y-4 pr-2">
            {medications.map((med, index) => (
              <div key={index} className="p-4 bg-ink-50 rounded-xl border border-ink-200 space-y-3">
                <div className="flex justify-between items-center mb-1">
                  <h4 className="font-semibold text-sm text-ink-900">Medication {index + 1}</h4>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <Input 
                    label="Medicine Name" 
                    required 
                    value={med.name} 
                    onChange={e => handleMedChange(index, "name", e.target.value)} 
                  />
                  <Input 
                    label="Dosage (e.g. 500 mg)" 
                    required 
                    value={med.dosage} 
                    onChange={e => handleMedChange(index, "dosage", e.target.value)} 
                  />
                  <Input 
                    label="Frequency" 
                    placeholder="e.g. Twice daily"
                    value={med.frequency} 
                    onChange={e => handleMedChange(index, "frequency", e.target.value)} 
                  />
                  <Input 
                    label="Duration" 
                    placeholder="e.g. 5 days"
                    value={med.duration} 
                    onChange={e => handleMedChange(index, "duration", e.target.value)} 
                  />
                  <div className="col-span-2">
                    <Input 
                      label="Instructions" 
                      placeholder="e.g. After food"
                      value={med.instructions} 
                      onChange={e => handleMedChange(index, "instructions", e.target.value)} 
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
          
          <button type="button" onClick={handleAddRow} className="text-sm font-medium text-brand-600 hover:text-brand-700">
            + Add another medicine
          </button>

          <div className="flex justify-end gap-3 pt-4 border-t border-ink-100">
            <Button type="button" variant="secondary" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" loading={loading}>
              Confirm & Save
            </Button>
          </div>
        </form>
      </div>
    </Modal>
  );
}
