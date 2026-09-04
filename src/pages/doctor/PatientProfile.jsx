import React, { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  Plus,
  CalendarPlus,
  FlaskConical,
  UploadCloud,
  FileText,
  ExternalLink,
  ShieldAlert,
  ShieldCheck,
  Clock,
} from "lucide-react";
import Topbar from "../../components/layout/Topbar";
import RiskBadge from "../../components/healthcare/RiskBadge";
import RiskScore from "../../components/healthcare/RiskScore";
import Avatar from "../../components/ui/Avatar";
import Button from "../../components/ui/Button";
import Badge from "../../components/ui/Badge";
import CheckinSummary from "../../components/healthcare/CheckinSummary";
import MedicationCard from "../../components/healthcare/MedicationCard";
import AIHistorySummaryCard from "../../components/healthcare/AIHistorySummaryCard";
import EmptyState from "../../components/ui/EmptyState";
import Modal from "../../components/ui/Modal";
import Input from "../../components/ui/Input";
import MedicationFormModal from "../../components/healthcare/MedicationFormModal";
import LabOrderModal from "../../components/healthcare/LabOrderModal";
import DocumentUploadModal from "../../components/healthcare/DocumentUploadModal";
import PrescriptionVerificationModal from "../../components/healthcare/PrescriptionVerificationModal";
import { useData } from "../../context/DataContext";
import { getPatientAISummary } from "../../api/analytics.api";
import { orderLabTest } from "../../api/lab.api";
import { getDocuments, getDocumentViewUrl } from "../../api/documents.api";
import { formatRelativeTime, formatDayLabel, formatTime } from "../../utils/dateUtils";

const TABS = ["Overview", "Documents", "Check-ins", "Medications", "History", "Analytics"];

export default function PatientProfile() {
  const { id } = useParams();
  const navigate = useNavigate();
  const {
    getPatientById,
    getCheckinsForPatient,
    getMedicationsForPatient,
    addMedication,
    markMedicationStatus,
    updatePatient,
    refreshData,
  } = useData();

  const patient = getPatientById(id);
  const checkins = getCheckinsForPatient(id);
  const medications = getMedicationsForPatient(id);

  const [tab, setTab] = useState("Overview");
  const [medModalOpen, setMedModalOpen] = useState(false);
  const [labModalOpen, setLabModalOpen] = useState(false);
  const [docUploadOpen, setDocUploadOpen] = useState(false);
  const [verifyPrescriptionDoc, setVerifyPrescriptionDoc] = useState(null);
  const [followUpOpen, setFollowUpOpen] = useState(false);
  const [followUpForm, setFollowUpForm] = useState({ date: "", time: "10:30", reason: "" });
  const [aiSummary, setAiSummary] = useState(null);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [documents, setDocuments] = useState([]);
  const [docsLoading, setDocsLoading] = useState(false);

  const fetchSummary = useCallback(() => {
    if (id) {
      setSummaryLoading(true);
      getPatientAISummary(id)
        .then((data) => setAiSummary(data))
        .catch(console.error)
        .finally(() => setSummaryLoading(false));
    }
  }, [id]);

  const fetchDocList = useCallback(() => {
    if (id) {
      setDocsLoading(true);
      getDocuments({ patientId: id })
        .then((data) => {
          const list = Array.isArray(data) ? data : data.results || [];
          setDocuments(list);
        })
        .catch((err) => console.error("Error fetching patient documents:", err))
        .finally(() => setDocsLoading(false));
    }
  }, [id]);

  useEffect(() => {
    fetchSummary();
    fetchDocList();
  }, [fetchSummary, fetchDocList]);

  if (!patient) {
    return (
      <>
        <Topbar title="Patient not found" />
        <main className="flex-1 px-6 py-6">
          <EmptyState title="We couldn't find this patient" description="They may have been removed." />
        </main>
      </>
    );
  }

  function handleScheduleFollowUp(e) {
    e.preventDefault();
    if (!followUpForm.date) return;
    const date = new Date(`${followUpForm.date}T${followUpForm.time || "10:00"}`);
    updatePatient(patient.id, {
      nextFollowUp: { doctorName: "Dr. Sarah Chen", date, reason: followUpForm.reason || "Follow-up review" },
    });
    setFollowUpOpen(false);
  }

  async function handleOrderLab({ testName, priority, notes }) {
    await orderLabTest({ patientId: patient.id, testName, priority, notes });
    fetchSummary();
  }

  function handleDocumentUploaded() {
    fetchDocList();
    fetchSummary();
  }

  function handlePrescriptionVerified() {
    fetchDocList();
    fetchSummary();
    if (refreshData) refreshData();
  }

  return (
    <>
      <Topbar title={patient.name} subtitle={patient.condition} />
      <main className="flex-1 px-6 py-6">
        <button
          onClick={() => navigate("/doctor/patients")}
          className="mb-4 flex items-center gap-1.5 text-sm font-medium text-ink-500 hover:text-ink-900"
        >
          <ArrowLeft size={15} /> Patients
        </button>

        <div className="flex flex-col gap-4 rounded-2xl border border-ink-300/15 bg-white p-6 shadow-card sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-4">
            <Avatar name={patient.name} initials={patient.avatarInitials} size="lg" />
            <div>
              <h1 className="text-lg font-semibold text-ink-900">{patient.name}</h1>
              <p className="text-sm text-ink-500">
                {patient.age} years · {patient.condition}
              </p>
              <div className="mt-2 flex items-center gap-2">
                <RiskBadge level={patient.riskLevel} />
                <span className="text-xs text-ink-400">AI Score {patient.riskScore}</span>
              </div>
              <p className="mt-1 text-xs text-ink-300">
                Last check-in: {patient.lastCheckIn ? formatRelativeTime(patient.lastCheckIn) : "No check-ins yet"}
              </p>
            </div>
          </div>
          <div className="flex shrink-0 flex-wrap gap-2">
            <Button variant="secondary" leftIcon={<UploadCloud size={15} />} onClick={() => setDocUploadOpen(true)}>
              Upload Document
            </Button>
            <Button variant="secondary" leftIcon={<Plus size={15} />} onClick={() => setMedModalOpen(true)}>
              Add Medication
            </Button>
            <Button variant="secondary" leftIcon={<FlaskConical size={15} />} onClick={() => setLabModalOpen(true)}>
              Order Lab Test
            </Button>
            <Button variant="secondary" leftIcon={<CalendarPlus size={15} />} onClick={() => setFollowUpOpen(true)}>
              Schedule Follow-up
            </Button>
          </div>
        </div>

        <div className="no-scrollbar mt-6 flex gap-1 overflow-x-auto border-b border-ink-300/15">
          {TABS.map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`whitespace-nowrap border-b-2 px-4 py-2.5 text-sm font-medium transition ${
                tab === t ? "border-brand-700 text-brand-800" : "border-transparent text-ink-500 hover:text-ink-800"
              }`}
            >
              {t}
            </button>
          ))}
        </div>

        <div className="mt-6">
          {tab === "Overview" && (
            <div className="grid gap-6 lg:grid-cols-3">
              <div className="rounded-2xl border border-ink-300/15 bg-white p-6 shadow-card lg:col-span-2">
                <h2 className="text-sm font-semibold uppercase tracking-wide text-ink-500">Current AI Assessment</h2>
                <div className="mt-4 flex items-start gap-5">
                  <RiskScore score={patient.riskScore} level={patient.riskLevel} size={84} />
                  <div className="flex-1">
                    <RiskBadge level={patient.riskLevel} />
                    <p className="mt-3 text-xs font-semibold uppercase tracking-wide text-ink-300">Reason</p>
                    <p className="mt-1 text-sm text-ink-800">{patient.reason}</p>
                    <p className="mt-3 text-xs font-semibold uppercase tracking-wide text-ink-300">Recommended Action</p>
                    <p className="mt-1 text-sm text-ink-800">{patient.followUpAction}</p>
                  </div>
                </div>
              </div>

              <div className="rounded-2xl border border-ink-300/15 bg-white p-6 shadow-card">
                <h2 className="text-sm font-semibold uppercase tracking-wide text-ink-500">Medication Adherence</h2>
                <p className="mt-3 text-2xl font-bold text-ink-900">{patient.medicationAdherencePct}%</p>
                <p className="text-xs text-ink-500">This week</p>
                <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-ink-900/5">
                  <div
                    className="h-full rounded-full bg-brand-600"
                    style={{ width: `${patient.medicationAdherencePct}%` }}
                  />
                </div>
              </div>

              {/* AI Clinical Brief & History Summary */}
              <div className="lg:col-span-3">
                <AIHistorySummaryCard summary={aiSummary} loading={summaryLoading} />
              </div>

              <div className="rounded-2xl border border-ink-300/15 bg-white p-6 shadow-card lg:col-span-2">
                <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-ink-500">Recent Check-ins</h2>
                {checkins.length ? (
                  <div className="space-y-3">
                    {checkins.slice(0, 3).map((c) => (
                      <CheckinSummary key={c.id} checkin={c} />
                    ))}
                  </div>
                ) : (
                  <EmptyState title="No check-ins yet" description="They will appear here once the patient checks in." />
                )}
              </div>

              <div className="rounded-2xl border border-ink-300/15 bg-white p-6 shadow-card">
                <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-ink-500">Medical Summary</h2>
                <dl className="space-y-2.5 text-sm">
                  <div>
                    <dt className="text-xs text-ink-400">Diagnosis</dt>
                    <dd className="text-ink-800">{patient.diagnosis}</dd>
                  </div>
                  <div>
                    <dt className="text-xs text-ink-400">Allergies</dt>
                    <dd className="text-ink-800">{patient.allergies}</dd>
                  </div>
                  <div>
                    <dt className="text-xs text-ink-400">Caretaker</dt>
                    <dd className="text-ink-800">
                      {patient.caretaker?.name} · {patient.caretaker?.relationship} · {patient.caretaker?.phone}
                    </dd>
                  </div>
                </dl>
              </div>
            </div>
          )}

          {tab === "Documents" && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-base font-semibold text-ink-900">Patient Clinical Documents & Lab Reports</h2>
                  <p className="text-xs text-ink-500">
                    Uploaded diagnostic files, prescriptions, and reports parsed with OCR and indexed for patient-scoped RAG.
                  </p>
                </div>
                <Button leftIcon={<UploadCloud size={15} />} onClick={() => setDocUploadOpen(true)}>
                  Upload Document
                </Button>
              </div>

              {docsLoading ? (
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="h-32 rounded-2xl bg-ink-100 animate-pulse" />
                  <div className="h-32 rounded-2xl bg-ink-100 animate-pulse" />
                </div>
              ) : documents.length ? (
                <div className="grid gap-4 sm:grid-cols-2">
                  {documents.map((doc) => {
                    const findings = doc.extracted_data?.clinical_findings || [];
                    const isCandidatePrescription =
                      doc.document_type === "PRESCRIPTION" ||
                      findings.some((f) => f.entity_type === "CANDIDATE_PRESCRIPTION");
                    const needsReview = doc.status === "REVIEW_REQUIRED" || (isCandidatePrescription && doc.status !== "VERIFIED");

                    return (
                      <div
                        key={doc.id}
                        className="rounded-2xl border border-ink-300/15 bg-white p-5 shadow-card space-y-3 flex flex-col justify-between"
                      >
                        <div>
                          <div className="flex items-start justify-between gap-2">
                            <div className="flex items-center gap-2">
                              <FileText size={18} className="text-brand-600 shrink-0" />
                              <h3 className="font-semibold text-sm text-ink-900">{doc.title}</h3>
                            </div>
                            <Badge
                              variant={
                                doc.status === "VERIFIED" || doc.status === "COMPLETED"
                                  ? "success"
                                  : doc.status === "REVIEW_REQUIRED"
                                  ? "warning"
                                  : "neutral"
                              }
                              size="sm"
                            >
                              {doc.status}
                            </Badge>
                          </div>

                          <p className="mt-1 text-xs text-ink-400">
                            {doc.document_type} · {doc.created_at ? new Date(doc.created_at).toLocaleDateString() : ""}
                          </p>

                          {/* Extracted Findings Preview */}
                          {findings.length > 0 && (
                            <div className="mt-3 rounded-xl bg-canvas-soft/60 p-2.5 border border-ink-100 text-xs space-y-1">
                              <span className="font-semibold text-ink-500 text-[11px] uppercase tracking-wider">
                                Extracted Findings:
                              </span>
                              <div className="flex flex-wrap gap-1.5 mt-1">
                                {findings.map((f, i) => (
                                  <span
                                    key={i}
                                    className="bg-white px-2 py-0.5 rounded border border-ink-200 text-ink-800 text-[11px] font-medium"
                                  >
                                    {f.entity_type === "BIOMARKER" && `${f.biomarker_name}: ${f.value} ${f.unit || ""}`}
                                    {f.entity_type === "CANDIDATE_PRESCRIPTION" && `Rx: ${f.drug_name} ${f.dosage || ""}`}
                                    {f.entity_type === "CLINICAL_NOTE" && f.text?.slice(0, 30)}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>

                        {/* Actions */}
                        <div className="pt-2 border-t border-ink-100 flex items-center justify-between gap-2">
                          <Button
                            size="sm"
                            variant="secondary"
                            className="text-xs"
                            onClick={() => window.open(getDocumentViewUrl(doc.id), "_blank")}
                          >
                            <ExternalLink size={13} className="mr-1 inline" />
                            View Original Report
                          </Button>

                          {needsReview && (
                            <Button
                              size="sm"
                              className="text-xs bg-amber-600 hover:bg-amber-700 text-white"
                              onClick={() => setVerifyPrescriptionDoc(doc)}
                            >
                              <ShieldCheck size={13} className="mr-1 inline" />
                              Review & Verify Rx
                            </Button>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <EmptyState
                  title="No clinical documents uploaded"
                  description="Upload lab reports, scans, or prescriptions to enable OCR extraction and patient-scoped RAG retrieval."
                  action={
                    <Button leftIcon={<UploadCloud size={15} />} onClick={() => setDocUploadOpen(true)}>
                      Upload Document
                    </Button>
                  }
                />
              )}
            </div>
          )}

          {tab === "Check-ins" &&
            (checkins.length ? (
              <div className="grid gap-3 sm:grid-cols-2">
                {checkins.map((c) => (
                  <CheckinSummary key={c.id} checkin={c} />
                ))}
              </div>
            ) : (
              <EmptyState title="No check-ins yet" description="Daily check-ins will appear here." />
            ))}

          {tab === "Medications" &&
            (medications.length ? (
              <div className="grid gap-3 sm:grid-cols-2">
                {medications.map((m) => (
                  <MedicationCard
                    key={m.id}
                    medication={m}
                    onMarkTaken={() => markMedicationStatus(m.id, "TAKEN")}
                    onMarkMissed={() => markMedicationStatus(m.id, "MISSED")}
                  />
                ))}
              </div>
            ) : (
              <EmptyState
                title="No medications yet"
                description="Add a medication to get started."
                action={
                  <Button size="sm" onClick={() => setMedModalOpen(true)}>
                    Add Medication
                  </Button>
                }
              />
            ))}

          {tab === "History" && (
            <div className="space-y-6">
              <AIHistorySummaryCard summary={aiSummary} loading={summaryLoading} />
              <div className="space-y-1">
                {checkins.length ? (
                  checkins.map((c, i) => (
                    <div key={c.id} className="flex gap-3">
                      <div className="flex flex-col items-center">
                        <span className="mt-1.5 h-2 w-2 rounded-full bg-brand-500" />
                        {i !== checkins.length - 1 && <span className="mt-1 w-px flex-1 bg-ink-300/20" />}
                      </div>
                      <div className="pb-4">
                        <p className="text-xs text-ink-300">
                          {formatDayLabel(c.date)} · {formatTime(c.date)}
                        </p>
                        <p className="text-sm font-medium text-ink-900">Daily Check-in</p>
                        <div className="mt-1">
                          <RiskBadge level={c.riskLevel} size="sm" />
                        </div>
                      </div>
                    </div>
                  ))
                ) : (
                  <EmptyState title="No history yet" description="Patient activity will build a timeline here." />
                )}
              </div>
            </div>
          )}

          {tab === "Analytics" && (
            <div className="space-y-6">
              <AIHistorySummaryCard summary={aiSummary} loading={summaryLoading} />
            </div>
          )}
        </div>
      </main>

      <MedicationFormModal
        open={medModalOpen}
        onClose={() => setMedModalOpen(false)}
        onSubmit={(form) => addMedication(patient.id, form)}
      />

      <LabOrderModal
        open={labModalOpen}
        onClose={() => setLabModalOpen(false)}
        onSubmit={handleOrderLab}
      />

      <DocumentUploadModal
        open={docUploadOpen}
        onClose={() => setDocUploadOpen(false)}
        patientId={patient.id}
        onUploaded={handleDocumentUploaded}
      />

      <PrescriptionVerificationModal
        open={!!verifyPrescriptionDoc}
        onClose={() => setVerifyPrescriptionDoc(null)}
        document={verifyPrescriptionDoc}
        onVerified={handlePrescriptionVerified}
      />

      <Modal open={followUpOpen} onClose={() => setFollowUpOpen(false)} title="Schedule Follow-up">
        <form onSubmit={handleScheduleFollowUp} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Date"
              type="date"
              required
              value={followUpForm.date}
              onChange={(e) => setFollowUpForm((f) => ({ ...f, date: e.target.value }))}
            />
            <Input
              label="Time"
              type="time"
              value={followUpForm.time}
              onChange={(e) => setFollowUpForm((f) => ({ ...f, time: e.target.value }))}
            />
          </div>
          <Input
            label="Reason"
            placeholder="e.g. Post-op review"
            value={followUpForm.reason}
            onChange={(e) => setFollowUpForm((f) => ({ ...f, reason: e.target.value }))}
          />
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="secondary" onClick={() => setFollowUpOpen(false)}>
              Cancel
            </Button>
            <Button type="submit">Schedule</Button>
          </div>
        </form>
      </Modal>
    </>
  );
}

