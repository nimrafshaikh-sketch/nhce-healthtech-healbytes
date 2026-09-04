import React, { useState } from "react";
import { UploadCloud, Sparkles, FileText, CheckCircle2, AlertCircle, Plus, Trash2, Camera } from "lucide-react";
import Modal from "../ui/Modal";
import Input from "../ui/Input";
import Button from "../ui/Button";
import { createPrescription } from "../../api/prescription.api";
import { uploadDocument } from "../../api/documents.api";

export default function PrescriptionFormModal({ open, onClose, onSuccess, patientId }) {
  const [activeTab, setActiveTab] = useState("upload"); // 'upload' | 'manual'
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  // Upload mode states
  const [file, setFile] = useState(null);
  const [filePreview, setFilePreview] = useState(null);
  const [title, setTitle] = useState("");

  // Manual mode states
  const [medications, setMedications] = useState([
    { name: "", dosage: "", frequency: "", duration: "", instructions: "" }
  ]);

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      const selected = e.target.files[0];
      setFile(selected);
      if (!title) {
        setTitle(selected.name.replace(/\.[^/.]+$/, ""));
      }
      if (selected.type.startsWith("image/")) {
        const reader = new FileReader();
        reader.onloadend = () => setFilePreview(reader.result);
        reader.readAsDataURL(selected);
      } else {
        setFilePreview(null);
      }
    }
  };

  const handleUploadSubmit = async (e) => {
    e.preventDefault();
    if (!file) {
      setError("Please select a prescription image or document file.");
      return;
    }
    setLoading(true);
    setError(null);

    const formData = new FormData();
    formData.append("patient", patientId);
    formData.append("title", title || `Prescription - ${file.name}`);
    formData.append("document_type", "PRESCRIPTION");
    formData.append("file", file);

    try {
      const res = await uploadDocument(formData);
      setSuccessMsg("Prescription processed! Medications auto-extracted and added to patient dashboard.");
      setTimeout(() => {
        setSuccessMsg(null);
        setFile(null);
        setFilePreview(null);
        setTitle("");
        if (onSuccess) onSuccess(res);
        if (onClose) onClose();
      }, 1200);
    } catch (err) {
      setError(err.message || "Failed to upload and process prescription document.");
    } finally {
      setLoading(false);
    }
  };

  const handleAddRow = () => {
    setMedications([...medications, { name: "", dosage: "", frequency: "", duration: "", instructions: "" }]);
  };

  const handleRemoveRow = (index) => {
    if (medications.length === 1) return;
    setMedications(medications.filter((_, i) => i !== index));
  };

  const handleMedChange = (index, field, value) => {
    const newMeds = [...medications];
    newMeds[index][field] = value;
    setMedications(newMeds);
  };

  const handleManualSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const validMeds = medications.filter(m => m.name && m.dosage);
      if (validMeds.length === 0) {
        setError("Please add at least one medication with a name and dosage.");
        setLoading(false);
        return;
      }
      const res = await createPrescription({
        patientId,
        medications: validMeds,
      });
      setSuccessMsg("Prescription issued successfully!");
      setTimeout(() => {
        setSuccessMsg(null);
        if (onSuccess) onSuccess(res);
        if (onClose) onClose();
      }, 1000);
    } catch (err) {
      setError(err.message || "Failed to create prescription.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal open={open} onClose={onClose} title="Issue or Upload Prescription">
      <div className="space-y-4">
        {/* Navigation Tabs */}
        <div className="flex rounded-xl bg-ink-100 p-1">
          <button
            type="button"
            onClick={() => { setActiveTab("upload"); setError(null); }}
            className={`flex flex-1 items-center justify-center gap-2 rounded-lg py-2 text-xs font-semibold transition ${
              activeTab === "upload"
                ? "bg-white text-brand-700 shadow-sm"
                : "text-ink-600 hover:text-ink-900"
            }`}
          >
            <Sparkles size={14} className="text-brand-600" />
            Upload Photo / Doc (Auto-Extract Meds)
          </button>
          <button
            type="button"
            onClick={() => { setActiveTab("manual"); setError(null); }}
            className={`flex flex-1 items-center justify-center gap-2 rounded-lg py-2 text-xs font-semibold transition ${
              activeTab === "manual"
                ? "bg-white text-ink-900 shadow-sm"
                : "text-ink-600 hover:text-ink-900"
            }`}
          >
            <FileText size={14} />
            Enter Manually
          </button>
        </div>

        {error && (
          <div className="flex items-center gap-2 rounded-xl border border-red-200 bg-red-50 p-3 text-xs text-red-700">
            <AlertCircle size={15} className="shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {successMsg ? (
          <div className="py-8 text-center space-y-3">
            <div className="h-12 w-12 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center mx-auto animate-bounce">
              <CheckCircle2 size={28} />
            </div>
            <p className="text-base font-bold text-ink-900">{successMsg}</p>
            <p className="text-xs text-ink-500">Updating medications, reminders, and clinical records...</p>
          </div>
        ) : activeTab === "upload" ? (
          /* Upload & Auto-Extract Mode */
          <form onSubmit={handleUploadSubmit} className="space-y-4">
            <div className="rounded-xl border border-brand-200 bg-brand-50/60 p-3.5 flex items-start gap-2.5">
              <Sparkles size={16} className="text-brand-600 shrink-0 mt-0.5" />
              <div className="text-xs text-brand-900 space-y-1">
                <p className="font-semibold">Zero manual entry required</p>
                <p className="text-brand-700">
                  Upload a photo or scanned PDF of the handwritten/printed prescription. Our OCR engine automatically extracts all tablets, dosages, and schedules them on the patient dashboard (`⏰ 8:00 AM`, `⏰ 8:00 PM`).
                </p>
              </div>
            </div>

            <Input
              label="Prescription Label / Title"
              placeholder="e.g. Cardiology Prescription - Dr. Sharma"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />

            {/* File Dropzone */}
            <div className="space-y-1">
              <label className="text-xs font-semibold text-ink-700">Prescription Photo or Document (PNG, JPG, PDF)</label>
              <div className="relative border-2 border-dashed border-ink-300 hover:border-brand-500 rounded-2xl p-6 text-center bg-canvas-soft/60 transition group cursor-pointer">
                <input
                  type="file"
                  accept="image/png,image/jpeg,image/jpg,image/webp,application/pdf"
                  onChange={handleFileChange}
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                  required={!file}
                />
                {filePreview ? (
                  <div className="space-y-2">
                    <img src={filePreview} alt="Prescription preview" className="max-h-36 mx-auto rounded-lg shadow-sm border border-ink-200 object-contain" />
                    <p className="text-xs font-semibold text-ink-800">{file.name} ({(file.size / 1024).toFixed(1)} KB)</p>
                    <p className="text-[11px] text-brand-600">Click or drag another image to replace</p>
                  </div>
                ) : file ? (
                  <div className="flex items-center justify-center gap-2 text-sm font-semibold text-ink-900">
                    <FileText size={22} className="text-brand-700" />
                    <span>{file.name}</span>
                    <span className="text-xs text-ink-400">({(file.size / 1024).toFixed(1)} KB)</span>
                  </div>
                ) : (
                  <div className="space-y-2 text-ink-500">
                    <div className="mx-auto w-12 h-12 rounded-full bg-brand-50 text-brand-600 flex items-center justify-center group-hover:scale-110 transition">
                      <Camera size={24} />
                    </div>
                    <div>
                      <p className="text-xs font-semibold text-ink-800">
                        Click to take/upload photo or browse file
                      </p>
                      <p className="text-[11px] text-ink-400 mt-0.5">Supports PNG, JPG, WebP, PDF</p>
                    </div>
                  </div>
                )}
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-ink-100">
              <Button type="button" variant="ghost" onClick={onClose}>
                Cancel
              </Button>
              <Button type="submit" loading={loading} leftIcon={<Sparkles size={14} />}>
                Upload & Auto-Extract Tablets
              </Button>
            </div>
          </form>
        ) : (
          /* Manual Entry Mode */
          <form onSubmit={handleManualSubmit} className="space-y-4">
            <div className="max-h-80 overflow-y-auto space-y-3 pr-1">
              {medications.map((med, index) => (
                <div key={index} className="p-3.5 bg-ink-50 rounded-xl border border-ink-200 space-y-2.5">
                  <div className="flex justify-between items-center">
                    <h4 className="font-semibold text-xs text-ink-900 uppercase tracking-wider">Medication #{index + 1}</h4>
                    {medications.length > 1 && (
                      <button
                        type="button"
                        onClick={() => handleRemoveRow(index)}
                        className="text-xs text-red-500 hover:text-red-700 flex items-center gap-1"
                      >
                        <Trash2 size={12} /> Remove
                      </button>
                    )}
                  </div>
                  <div className="grid grid-cols-2 gap-2.5">
                    <Input 
                      label="Medicine Name" 
                      required 
                      placeholder="e.g. Paracetamol"
                      value={med.name} 
                      onChange={e => handleMedChange(index, "name", e.target.value)} 
                    />
                    <Input 
                      label="Dosage" 
                      required 
                      placeholder="e.g. 500 mg"
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
                        placeholder="e.g. Take after meals with warm water"
                        value={med.instructions} 
                        onChange={e => handleMedChange(index, "instructions", e.target.value)} 
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>

            <button
              type="button"
              onClick={handleAddRow}
              className="flex items-center gap-1 text-xs font-semibold text-brand-600 hover:text-brand-700"
            >
              <Plus size={14} /> Add another medication
            </button>

            <div className="flex justify-end gap-2 pt-2 border-t border-ink-100">
              <Button type="button" variant="ghost" onClick={onClose}>
                Cancel
              </Button>
              <Button type="submit" loading={loading}>
                Save Prescription
              </Button>
            </div>
          </form>
        )}
      </div>
    </Modal>
  );
}
