import React, { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeft, Plus, CalendarPlus, FileText, FlaskConical } from "lucide-react";
import Topbar from "../../components/layout/Topbar";
import RiskBadge from "../../components/healthcare/RiskBadge";
import RiskScore from "../../components/healthcare/RiskScore";
import Avatar from "../../components/ui/Avatar";
import Button from "../../components/ui/Button";
import CheckinSummary from "../../components/healthcare/CheckinSummary";
import MedicationCard from "../../components/healthcare/MedicationCard";
import AIHistorySummaryCard from "../../components/healthcare/AIHistorySummaryCard";
import EmptyState from "../../components/ui/EmptyState";
import Modal from "../../components/ui/Modal";
import Input from "../../components/ui/Input";
import MedicationFormModal from "../../components/healthcare/MedicationFormModal";
import PrescriptionFormModal from "../../components/doctor/PrescriptionFormModal";
import LabOrderFormModal from "../../components/doctor/LabOrderFormModal";
import { useData } from "../../context/DataContext";
import { getPatientAISummary } from "../../api/analytics.api";
import { formatRelativeTime, formatDayLabel, formatTime } from "../../utils/dateUtils";
import { getPrescriptionsForPatient } from "../../api/prescription.api";
import { getLabResultsForPatient } from "../../api/lab.api";
import { useAuth } from "../../context/AuthContext";

const TABS = ["Overview", "Check-ins", "Medications", "Prescriptions", "Labs", "History", "Analytics"];

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
  } = useData();

  const patient = getPatientById(id);
  const checkins = getCheckinsForPatient(id);
  const medications = getMedicationsForPatient(id);

  const [tab, setTab] = useState("Overview");
  const [medModalOpen, setMedModalOpen] = useState(false);
  const [prescModalOpen, setPrescModalOpen] = useState(false);
  const [labModalOpen, setLabModalOpen] = useState(false);
  const [followUpOpen, setFollowUpOpen] = useState(false);
  const [followUpForm, setFollowUpForm] = useState({ date: "", time: "10:30", reason: "" });
  const [aiSummary, setAiSummary] = useState(null);
  const [summaryLoading, setSummaryLoading] = useState(false);

  useEffect(() => {
    let active = true;
    if (id) {
      setSummaryLoading(true);
      getPatientAISummary(id)
        .then((data) => {
          if (active) setAiSummary(data);
        })
        .catch((err) => {
          console.error("AI summary error:", err);
        })
        .finally(() => {
          if (active) setSummaryLoading(false);
        });
    }
    return () => {
      active = false;
    };
  }, [id]);

  const [prescriptions, setPrescriptions] = useState([]);
  const [labs, setLabs] = useState([]);

  const fetchData = async () => {
    if (patient) {
      const pData = await getPrescriptionsForPatient(patient.id);
      setPrescriptions(pData);
      const lData = await getLabResultsForPatient(patient.id);
      setLabs(lData);
    }
  };

  useEffect(() => {
    fetchData();
  }, [patient?.id]);

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
      nextFollowUp: { doctorName: user?.name || "Dr. Sarah Chen", date, reason: followUpForm.reason || "Follow-up review" },
    });
    setFollowUpOpen(false);
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
            <Button variant="secondary" leftIcon={<FileText size={15} />} onClick={() => setPrescModalOpen(true)}>
              Prescribe
            </Button>
            <Button variant="secondary" leftIcon={<FlaskConical size={15} />} onClick={() => setLabModalOpen(true)}>
              Order Lab
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

              {/* AI Clinical History Summary */}
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

          {tab === "Prescriptions" && (
            <div className="space-y-4">
              {prescriptions.length === 0 ? (
                <EmptyState title="No prescriptions" description="You haven't issued any prescriptions for this patient." />
              ) : (
                prescriptions.map((p) => (
                  <div key={p.id} className="bg-white rounded-xl shadow-sm border border-brand-200 p-4">
                    <div className="flex justify-between items-start mb-2">
                      <h3 className="font-bold text-brand-800">Prescription Issued</h3>
                      <span className="text-xs text-ink-400">{new Date(p.date).toLocaleDateString()}</span>
                    </div>
                    <div className="space-y-2 mt-3">
                      {p.medications.map((m, idx) => (
                        <div key={idx} className="bg-brand-50 p-3 rounded-lg border border-brand-100 flex justify-between items-center">
                          <div>
                            <p className="font-bold text-brand-900">{m.name} - {m.dosage}</p>
                            <p className="text-sm text-brand-700 mt-1">
                              {m.frequency} for {m.duration}
                            </p>
                          </div>
                          <span className="text-xs text-brand-600 font-medium">{m.instructions}</span>
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
                <EmptyState title="No lab results" description="No lab results are available." />
              ) : (
                labs.map((res) => (
                  <div key={res.id} className="bg-white rounded-xl shadow-sm border border-ink-200 p-5">
                    <div className="flex justify-between items-start mb-4">
                      <div>
                        <h3 className="font-bold text-ink-900">{res.testType}</h3>
                        <p className="text-xs text-ink-500">{new Date(res.date).toLocaleDateString()}</p>
                      </div>
                      <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${res.releaseStatus === 'RELEASED' ? 'bg-green-50 text-green-700' : 'bg-amber-50 text-amber-700'}`}>
                        {res.releaseStatus === 'RELEASED' ? 'Released to Patient' : 'Review Needed'}
                      </span>
                    </div>
                    <div className="space-y-3 border-t border-ink-100 pt-4">
                      {res.values.map((v, i) => (
                        <div key={i} className="flex justify-between items-center text-sm">
                          <span className="font-medium text-ink-700">{v.name}</span>
                          <div className="flex items-center gap-3">
                            <span className={`font-bold ${v.flag !== 'NORMAL' ? 'text-red-600' : 'text-ink-900'}`}>
                              {v.value} <span className="font-normal text-ink-500 text-xs">{v.unit}</span>
                            </span>
                            <span className="text-xs text-ink-400 w-16 text-right">{v.referenceRange}</span>
                          </div>
                        </div>
                      ))}
                      {res.aiAnalysis && (
                        <div className="mt-4 bg-brand-50 p-3 rounded-lg border border-brand-100 text-sm text-brand-800">
                          <strong>AI Summary:</strong> {res.aiAnalysis}
                        </div>
                      )}
                    </div>
                  </div>
                ))
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
        onClose={() => setMedModalOpen(false)}
        onSubmit={(form) => addMedication(patient.id, form)}
      />

      <PrescriptionFormModal
        open={prescModalOpen}
        onClose={() => { setPrescModalOpen(false); fetchData(); }}
        patientId={patient.id}
        doctorId={user?.id}
      />

      <LabOrderFormModal
        open={labModalOpen}
        onClose={() => setLabModalOpen(false)}
        patientId={patient.id}
        patientName={patient.name}
        doctorId={user?.id}
        doctorName={user?.name}
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
