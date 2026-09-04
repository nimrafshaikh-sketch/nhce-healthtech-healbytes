import React, { useState } from "react";
import { UploadCloud, FileText, CheckCircle2, AlertCircle, X } from "lucide-react";
import Modal from "../ui/Modal";
import Input from "../ui/Input";
import Button from "../ui/Button";
import { uploadDocument } from "../../api/documents.api";

const DOC_TYPES = [
  { value: "LAB_REPORT", label: "Laboratory Diagnostic Report" },
  { value: "PRESCRIPTION", label: "Prescription / Medication Order" },
  { value: "CONSULTATION", label: "Consultation / Progress Note" },
  { value: "DISCHARGE_SUMMARY", label: "Hospital Discharge Summary" },
  { value: "IMAGING_REPORT", label: "Imaging / Radiology Report" },
  { value: "OTHER", label: "Other Clinical Document" },
];

export default function DocumentUploadModal({ open, onClose, patientId, onUploaded }) {
  const [title, setTitle] = useState("");
  const [docType, setDocType] = useState("LAB_REPORT");
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  function handleFileChange(e) {
    if (e.target.files && e.target.files[0]) {
      const selected = e.target.files[0];
      setFile(selected);
      if (!title) {
        setTitle(selected.name.replace(/\.[^/.]+$/, ""));
      }
    }
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!file) {
      setError("Please select a medical document to upload.");
      return;
    }
    setUploading(true);
    setError(null);

    const formData = new FormData();
    formData.append("patient", patientId);
    formData.append("title", title || file.name);
    formData.append("document_type", docType);
    formData.append("file", file);

    try {
      const res = await uploadDocument(formData);
      setSuccess(true);
      setTimeout(() => {
        setSuccess(false);
        setFile(null);
        setTitle("");
        setDocType("LAB_REPORT");
        onClose();
        if (onUploaded) onUploaded(res);
      }, 1000);
    } catch (err) {
      setError(err.message || "Failed to upload document.");
    } finally {
      setUploading(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Upload Medical Document / Diagnostic Report">
      <form onSubmit={handleSubmit} className="space-y-4">
        {success ? (
          <div className="py-8 text-center text-emerald-600 space-y-2">
            <CheckCircle2 size={40} className="mx-auto" />
            <p className="text-base font-bold text-ink-900">Document Uploaded & Processed!</p>
            <p className="text-xs text-ink-500">Clinical entities extracted and indexed for RAG retrieval.</p>
          </div>
        ) : (
          <>
            {error && (
              <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-xs text-red-700">
                {error}
              </div>
            )}

            <Input
              label="Document Title / Report Heading"
              placeholder="e.g. Follow-up HbA1c Lab Report"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
            />

            <div className="space-y-1">
              <label className="text-xs font-semibold text-ink-700">Document Classification</label>
              <select
                value={docType}
                onChange={(e) => setDocType(e.target.value)}
                className="w-full rounded-xl border border-ink-200 bg-white px-3 py-2 text-sm text-ink-900 focus:border-brand-500 focus:outline-none"
              >
                {DOC_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>

            {/* File Dropzone */}
            <div className="space-y-1">
              <label className="text-xs font-semibold text-ink-700">Attach Document File (PDF, PNG, JPG, TXT)</label>
              <div className="relative border-2 border-dashed border-ink-200 hover:border-brand-400 rounded-2xl p-6 text-center bg-canvas-soft/50 transition">
                <input
                  type="file"
                  accept=".pdf,.png,.jpg,.jpeg,.txt"
                  onChange={handleFileChange}
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                  required={!file}
                />
                {file ? (
                  <div className="flex items-center justify-center gap-2 text-sm font-semibold text-ink-900">
                    <FileText size={20} className="text-brand-700" />
                    <span>{file.name}</span>
                    <span className="text-xs text-ink-400">({(file.size / 1024).toFixed(1)} KB)</span>
                  </div>
                ) : (
                  <div className="space-y-1 text-ink-500">
                    <UploadCloud size={32} className="mx-auto text-ink-400" />
                    <p className="text-xs font-semibold text-ink-800">
                      Click to browse or drag and drop document
                    </p>
                    <p className="text-[11px] text-ink-400">Supported formats: PDF, PNG, JPG up to 15MB</p>
                  </div>
                )}
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <Button type="button" variant="ghost" onClick={onClose}>
                Cancel
              </Button>
              <Button type="submit" loading={uploading}>
                Upload & Ingest Document
              </Button>
            </div>
          </>
        )}
      </form>
    </Modal>
  );
}
