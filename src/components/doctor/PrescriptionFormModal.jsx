import React, { useState } from "react";
import Modal from "./Modal";
import Input from "./Input";
import Button from "./Button";
import { Upload } from "lucide-react";
import { createPrescription, uploadPrescriptionImage } from "../../api/prescription.api";

export default function PrescriptionFormModal({ open, onClose, patientId, doctorId }) {
  const [loading, setLoading] = useState(false);
  const [ocrLoading, setOcrLoading] = useState(false);
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

  const handleImageUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setOcrLoading(true);
    try {
      const result = await uploadPrescriptionImage(file);
      if (result.success && result.extractedData) {
        setMedications(result.extractedData.medications);
        alert("Draft prescription extracted. Please verify the data.");
      }
    } catch (err) {
      alert("Failed to process image.");
    } finally {
      setOcrLoading(false);
    }
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
        doctorId,
        medications: validMeds,
      });
      alert("Prescription created successfully!");
      onClose();
    } catch (err) {
      alert("Failed to create prescription.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal open={open} onClose={onClose} title="Create Prescription">
      <div className="space-y-6">
        
        {/* OCR Section */}
        <div className="bg-brand-50 p-4 rounded-xl border border-brand-100 flex items-center justify-between">
          <div>
            <h4 className="font-bold text-brand-900 text-sm">Upload written prescription</h4>
            <p className="text-xs text-brand-700">AI will extract the details automatically.</p>
          </div>
          <label className={`cursor-pointer bg-white border border-brand-200 text-brand-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-brand-50 flex items-center gap-2 ${ocrLoading ? 'opacity-50 pointer-events-none' : ''}`}>
            <Upload size={16} />
            {ocrLoading ? "Extracting..." : "Upload Image"}
            <input type="file" accept="image/*" className="hidden" onChange={handleImageUpload} />
          </label>
        </div>

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
