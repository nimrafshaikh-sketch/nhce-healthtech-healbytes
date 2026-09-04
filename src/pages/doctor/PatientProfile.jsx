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
  ShieldCheck,
  Sparkles,
  Camera,
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
import PrescriptionFormModal from "../../components/doctor/PrescriptionFormModal";
import { useData } from "../../context/DataContext";
import { getPatientAISummary } from "../../api/analytics.api";
import { getPatientDetail } from "../../api/patients.api";
import { orderLabTest, getLabResultsForPatient, reviewLabResult } from "../../api/lab.api";
import { getDocuments, getDocumentViewUrl } from "../../api/documents.api";
import { getMedications, updateMedication } from "../../api/medication.api";
import { formatRelativeTime, formatDayLabel, formatTime } from "../../utils/dateUtils";
import { getPrescriptionsForPatient } from "../../api/prescription.api";
import { createAppointment } from "../../api/appointment.api";
import { useAuth } from "../../context/AuthContext";
import DoctorAgentChat from "../../components/doctor/DoctorAgentChat";

const TABS = ["Overview", "AI Copilot", "Documents", "Check-ins", "Medications", "Prescriptions", "Labs", "History", "Analytics"];

export default function PatientProfile() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const {
    getPatientById,
    getCheckinsForPatient,
    getMedicationsForPatient,
    addMedication,
    markMedicationStatus,
    updatePatient,
    refreshData,
  } = useData();

  const contextPatient = getPatientById(id);
  const [fetchedPatient, setFetchedPatient] = useState(null);
  const [patientLoading, setPatientLoading] = useState(false);
  const [fetchAttempted, setFetchAttempted] = useState(false);

  const patient = contextPatient || fetchedPatient;
  const effectiveId = patient?.id || (id && id !== "undefined" ? id : null);

  const checkins = getCheckinsForPatient(effectiveId) || [];
  const [liveMedications, setLiveMedications] = useState(null);
  const medications = liveMedications !== null ? liveMedications : getMedicationsForPatient(effectiveId) || [];

  const [tab, setTab] = useState("Overview");
  const [medModalOpen, setMedModalOpen] = useState(false);
  const [editingMedication, setEditingMedication] = useState(null);
  const [prescModalOpen, setPrescModalOpen] = useState(false);
  const [labModalOpen, setLabModalOpen] = useState(false);
  const [docUploadOpen, setDocUploadOpen] = useState(false);
  const [verifyPrescriptionDoc, setVerifyPrescriptionDoc] = useState(null);
  const [followUpOpen, setFollowUpOpen] = useState(false);
  const [followUpForm, setFollowUpForm] = useState({ date: "", time: "10:30", reason: "" });
  const [followUpSaving, setFollowUpSaving] = useState(false);
  const [followUpError, setFollowUpError] = useState(null);
  const [aiSummary, setAiSummary] = useState(null);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [documents, setDocuments] = useState([]);
  const [docsLoading, setDocsLoading] = useState(false);
  const [prescriptions, setPrescriptions] = useState([]);
  const [labs, setLabs] = useState([]);

  useEffect(() => {
    if (!id || id === "undefined") {
      setFetchAttempted(true);
      return;
    }
    if (!contextPatient) {
      setPatientLoading(true);
      getPatientDetail(id)
        .then((data) => {
          if (data) setFetchedPatient(data);
        })
        .catch((err) => {
          console.error("Error fetching patient detail:", err);
        })
        .finally(() => {
          setPatientLoading(false);
          setFetchAttempted(true);
        });
    } else {
      setFetchAttempted(true);
    }
  }, [id, contextPatient]);

  const fetchSummary = useCallback(() => {
    if (effectiveId && effectiveId !== "undefined") {
      setSummaryLoading(true);
      getPatientAISummary(effectiveId)
        .then((data) => setAiSummary(data))
        .catch(console.error)
        .finally(() => setSummaryLoading(false));
    }
  }, [effectiveId]);

  const fetchDocList = useCallback(() => {
    if (effectiveId && effectiveId !== "undefined") {
      setDocsLoading(true);
      getDocuments({ patientId: effectiveId })
        .then((data) => {
          const list = Array.isArray(data) ? data : data.results || [];
          setDocuments(list);
        })
        .catch((err) => console.error("Error fetching patient documents:", err))
        .finally(() => setDocsLoading(false));
    }
  }, [effectiveId]);

  const fetchPrescriptionsAndLabs = useCallback(async () => {
    if (effectiveId && effectiveId !== "undefined") {
      try {
        const pData = await getPrescriptionsForPatient(effectiveId);
        setPrescriptions(Array.isArray(pData) ? pData : []);
      } catch (e) {
        console.error("Error loading prescriptions:", e);
      }
      try {
        const lData = await getLabResultsForPatient(effectiveId);
        setLabs(Array.isArray(lData) ? lData : []);
      } catch (e) {
        console.error("Error loading labs:", e);
      }
    }
  }, [effectiveId]);

  const fetchMedications = useCallback(async () => {
    if (effectiveId && effectiveId !== "undefined") {
      try {
        const mData = await getMedications(effectiveId);
        setLiveMedications(Array.isArray(mData) ? mData : []);
      } catch (e) {
        console.error("Error loading medications:", e);
      }
    }
  }, [effectiveId]);

  useEffect(() => {
    if (effectiveId) {
      fetchSummary();
      fetchDocList();
      fetchPrescriptionsAndLabs();
      fetchMedications();
    }
  }, [effectiveId, fetchSummary, fetchDocList, fetchPrescriptionsAndLabs, fetchMedications]);

  if (patientLoading || (!patient && !fetchAttempted)) {
    return (
      <>
        <Topbar title="Loading patient..." />
        <main className="flex flex-1 items-center justify-center p-12">
          <div className="flex flex-col items-center gap-3">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-600 border-t-transparent" />
            <p className="text-sm font-medium text-ink-500">Loading patient chart...</p>
          </div>
        </main>
      </>
    );
  }

  if (!patient) {
    return (
      <>
        <Topbar title="Patient not found" />
        <main className="flex-1 px-6 py-6">
          <button
            onClick={() => navigate("/doctor/patients")}
            className="mb-4 flex items-center gap-1.5 text-sm font-medium text-ink-500 hover:text-ink-900"
          >
            <ArrowLeft size={15} /> Back to Patients
          </button>
          <EmptyState title="We couldn't find this patient" description="They may have been removed or the ID is invalid." />
        </main>
      </>
    );
  }

  async function handleScheduleFollowUp(e) {
    e.preventDefault();
    if (!followUpForm.date) return;
    const date = new Date(`${followUpForm.date}T${followUpForm.time || "10:00"}`);
    const reason = followUpForm.reason || "Follow-up review";

    // Local echo for instant UI feedback on this page's own "Next
    // Follow-up" display, plus the real, backend-persisted Appointment
    // (previously this was ONLY the local dispatch below - the appointment
    // never existed server-side, so it never showed up on the receptionist
    // dashboard or the patient's own appointments list).
    updatePatient(patient.id, {
      nextFollowUp: { doctorName: user?.name || "Doctor", date, reason },
    });

    setFollowUpSaving(true);
    setFollowUpError(null);
    try {
      await createAppointment({
        patientId: patient.id,
        doctorId: user?.id,
        scheduledAt: date.toISOString(),
        reason,
      });
      setFollowUpOpen(false);
      setFollowUpForm({ date: "", time: "10:30", reason: "" });
    } catch (err) {
      setFollowUpError(err.message || "Could not schedule this appointment. Please try again.");
    } finally {
      setFollowUpSaving(false);
    }
  }

  async function handleOrderLab({ testName, priority, notes }) {
    await orderLabTest({ patientId: patient.id, testName, priority, notes });
    fetchSummary();
    fetchPrescriptionsAndLabs();
  }

  async function handleReviewLabResult(resultId) {
    await reviewLabResult(resultId);
    fetchPrescriptionsAndLabs();
  }

  function handleDocumentUploaded() {
    fetchDocList();
    fetchSummary();
    fetchPrescriptionsAndLabs();
    fetchMedications();
    if (refreshData) refreshData();
  }

  function handlePrescriptionVerified() {
    fetchDocList();
    fetchSummary();
    fetchPrescriptionsAndLabs();
    fetchMedications();
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
            <Button variant="primary" leftIcon={<Sparkles size={15} />} onClick={() => setPrescModalOpen(true)}>
              Upload / Add Prescription
            </Button>
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

              {/* Live AI Copilot Assistant in Overview */}
              <div className="lg:col-span-3">
                <DoctorAgentChat patientId={patient.id} patientName={patient.name} />
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

          {tab === "AI Copilot" && (
            <div className="space-y-6">
              <div className="rounded-2xl border border-brand-200 bg-gradient-to-r from-brand-50 to-indigo-50/60 p-5 shadow-xs">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-600 text-white shadow-sm">
                    <Sparkles size={20} />
                  </div>
                  <div>
                    <h2 className="text-base font-bold text-ink-900">Dedicated AI Clinical Copilot Workspace</h2>
                    <p className="text-xs text-ink-600">
                      Chat with the patient's record in natural language. The Gemini engine autonomously queries live vitals, OCR prescriptions, lab results, and adherence metrics.
                    </p>
                  </div>
                </div>
              </div>
              <DoctorAgentChat patientId={patient.id} patientName={patient.name} />
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
                    readOnly={true}
                    onEdit={(med) => {
                      setEditingMedication(med);
                      setMedModalOpen(true);
                    }}
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

          {tab === "Prescriptions" && (
            <div className="space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white p-4 rounded-xl border border-brand-200 shadow-sm">
                <div>
                  <h3 className="font-bold text-ink-900 flex items-center gap-2">
                    Prescriptions & Medication Orders
                    <span className="text-[11px] font-semibold text-brand-700 bg-brand-50 px-2 py-0.5 rounded-full border border-brand-200">
                      OCR Auto-Extract Enabled
                    </span>
                  </h3>
                  <p className="text-xs text-ink-500 mt-0.5">
                    Upload a prescription photo/PDF to automatically extract tablets and schedule reminders on the patient dashboard.
                  </p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <Button size="sm" variant="primary" leftIcon={<Sparkles size={14} />} onClick={() => setPrescModalOpen(true)}>
                    Upload Prescription Photo
                  </Button>
                  <Button size="sm" variant="secondary" leftIcon={<Plus size={14} />} onClick={() => setPrescModalOpen(true)}>
                    Issue Manually
                  </Button>
                </div>
              </div>

              {prescriptions.length === 0 ? (
                <EmptyState
                  title="No prescriptions yet"
                  description="Upload a written prescription photo or issue one manually to schedule medications for this patient."
                  action={
                    <Button size="sm" leftIcon={<Sparkles size={14} />} onClick={() => setPrescModalOpen(true)}>
                      Upload Written Prescription
                    </Button>
                  }
                />
              ) : (
                prescriptions.map((p) => (
                  <div key={p.id} className="bg-white rounded-xl shadow-sm border border-brand-200 p-4">
                    <div className="flex justify-between items-start mb-2">
                      <div className="flex items-center gap-2">
                        <h3 className="font-bold text-brand-800">Prescription Issued</h3>
                        {p.status && (
                          <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800">
                            {p.status}
                          </span>
                        )}
                      </div>
                      <span className="text-xs text-ink-400">{new Date(p.date || p.created_at || Date.now()).toLocaleDateString()}</span>
                    </div>
                    <div className="space-y-2 mt-3">
                      {(p.medications || []).map((m, idx) => (
                        <div key={idx} className="bg-brand-50/70 p-3 rounded-lg border border-brand-100 flex justify-between items-center">
                          <div>
                            <p className="font-bold text-brand-900">{m.name} - {m.dosage}</p>
                            <p className="text-xs text-brand-700 mt-0.5">
                              {m.frequency} {m.duration ? `· ${m.duration}` : ""}
                            </p>
                          </div>
                          <span className="text-xs text-brand-700 bg-white/80 border border-brand-200 px-2 py-1 rounded font-medium">
                            {m.instructions || "⏰ 8:00 AM, 8:00 PM"}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {tab === "Labs" && (
            <div className="space-y-4">
              {labs.length === 0 ? (
                <EmptyState
                  title="No lab results"
                  description="No lab results are available."
                  action={
                    <Button size="sm" onClick={() => setLabModalOpen(true)}>
                      Order Lab Test
                    </Button>
                  }
                />
              ) : (
                labs.map((res) => {
                  const result = res.result;
                  return (
                  <div key={res.id} className="bg-white rounded-xl shadow-sm border border-ink-200 p-5">
                    <div className="flex justify-between items-start mb-4">
                      <div>
                        <h3 className="font-bold text-ink-900">{res.test_name || res.testType || "Lab Test"}</h3>
                        <p className="text-xs text-ink-500">{new Date(res.created_at || res.date || Date.now()).toLocaleDateString()}</p>
                      </div>
                      <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${res.status === 'completed' ? 'bg-green-50 text-green-700' : 'bg-amber-50 text-amber-700'}`}>
                        {res.status === 'completed' ? 'Completed' : res.status || 'Pending'}
                      </span>
                    </div>
                    <div className="space-y-3 border-t border-ink-100 pt-4">
                      {result?.result_text && (
                        <div className="bg-canvas-soft p-3 rounded-lg border border-ink-100 text-sm text-ink-800 whitespace-pre-wrap">
                          {result.result_text}
                        </div>
                      )}
                      {result?.ai_status && (
                        <div className="flex justify-between items-center text-sm">
                          <span className="font-medium text-ink-700">AI reference-range read</span>
                          <div className="flex items-center gap-3">
                            <span className={`font-bold ${result.ai_status !== 'NORMAL' ? 'text-red-600' : 'text-ink-900'}`}>
                              {result.ai_numeric_value != null ? `${result.ai_numeric_value}${result.ai_unit}` : result.ai_status}
                            </span>
                            {result.ai_reference_range && (
                              <span className="text-xs text-ink-400 w-24 text-right">{result.ai_reference_range}</span>
                            )}
                          </div>
                        </div>
                      )}
                      {result?.ai_explanation && (
                        <div className="bg-brand-50 p-3 rounded-lg border border-brand-100 text-sm text-brand-800">
                          <strong>AI Summary:</strong> {result.ai_explanation}
                        </div>
                      )}
                      {result?.notes && (
                        <div className="text-xs text-ink-500">
                          <strong>Notes:</strong> {result.notes}
                        </div>
                      )}
                      {result && !result.reviewed_at && (
                        <div className="pt-1">
                          <Button size="sm" variant="secondary" onClick={() => handleReviewLabResult(result.id)}>
                            Mark Reviewed
                          </Button>
                        </div>
                      )}
                      {result?.reviewed_at && (
                        <div className="text-xs text-green-700 flex items-center gap-1">
                          <ShieldCheck size={12} /> Reviewed {new Date(result.reviewed_at).toLocaleDateString()}
                        </div>
                      )}
                    </div>
                  </div>
                  );
                })
              )}
            </div>
          )}

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
        initialData={editingMedication}
        onClose={() => {
          setMedModalOpen(false);
          setEditingMedication(null);
        }}
        onSubmit={async (form) => {
          if (editingMedication) {
            await updateMedication(editingMedication.id, form);
          } else {
            await addMedication(patient.id, form);
          }
          fetchMedications();
          fetchPrescriptionsAndLabs();
          fetchSummary();
        }}
      />

      <LabOrderModal
        open={labModalOpen}
        onClose={() => setLabModalOpen(false)}
        onSubmit={handleOrderLab}
      />

      <PrescriptionFormModal
        open={prescModalOpen}
        onClose={() => {
          setPrescModalOpen(false);
          fetchPrescriptionsAndLabs();
          fetchMedications();
          fetchSummary();
        }}
        onSuccess={() => {
          setPrescModalOpen(false);
          fetchPrescriptionsAndLabs();
          fetchMedications();
          fetchSummary();
          fetchDocList();
          if (refreshData) refreshData();
        }}
        patientId={patient.id}
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
          {followUpError && (
            <p className="rounded-lg border border-risk-high/30 bg-risk-high-bg px-3 py-2 text-sm text-risk-high">
              {followUpError}
            </p>
          )}
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="secondary" onClick={() => setFollowUpOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={followUpSaving}>
              {followUpSaving ? "Scheduling…" : "Schedule"}
            </Button>
          </div>
        </form>
      </Modal>
    </>
  );
}
