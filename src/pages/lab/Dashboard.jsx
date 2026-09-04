import React, { useState, useEffect } from "react";
import {
  FlaskConical,
  ClipboardList,
  Clock,
  CheckCircle2,
  AlertCircle,
  FileText,
  User,
  Stethoscope,
  RefreshCw,
  Send,
  Play,
  ShieldCheck,
} from "lucide-react";
import Button from "../../components/ui/Button";
import Input from "../../components/ui/Input";
import Modal from "../../components/ui/Modal";
import { getLabRequests, claimLabRequest, recordLabResult } from "../../api/lab.api";

export default function LabDashboard() {
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState("all"); // 'all' | 'requested' | 'in_progress' | 'completed'

  // Modal State for Entering Results
  const [isResultModalOpen, setIsResultModalOpen] = useState(false);
  const [activeRequest, setActiveRequest] = useState(null);
  const [resultText, setResultText] = useState("");
  const [resultNotes, setResultNotes] = useState("");
  const [submittingResult, setSubmittingResult] = useState(false);
  const [resultError, setResultError] = useState(null);

  useEffect(() => {
    loadRequests();
  }, []);

  async function loadRequests() {
    setLoading(true);
    setError(null);
    try {
      const data = await getLabRequests();
      setRequests(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err.message || "Failed to load laboratory requests.");
    } finally {
      setLoading(false);
    }
  }

  async function handleClaim(request) {
    try {
      await claimLabRequest(request.id);
      loadRequests();
    } catch (err) {
      alert("Failed to claim request: " + (err.message || "Unknown error"));
    }
  }

  function openResultModal(request) {
    setActiveRequest(request);
    setResultText("");
    setResultNotes("");
    setResultError(null);
    setIsResultModalOpen(true);
  }

  async function handleSubmitResult(e) {
    e.preventDefault();
    if (!activeRequest) return;
    setSubmittingResult(true);
    setResultError(null);
    try {
      await recordLabResult(activeRequest.id, {
        resultText,
        notes: resultNotes,
      });
      setIsResultModalOpen(false);
      loadRequests();
    } catch (err) {
      setResultError(err.message || "Failed to submit laboratory results.");
    } finally {
      setSubmittingResult(false);
    }
  }

  const filteredRequests = requests.filter((r) => {
    if (filter === "all") return true;
    return r.status === filter;
  });

  const requestedCount = requests.filter((r) => r.status === "requested").length;
  const inProgressCount = requests.filter((r) => r.status === "in_progress").length;
  const completedCount = requests.filter((r) => r.status === "completed").length;

  return (
    <div className="space-y-8">
      {/* Header Banner */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-ink-900 tracking-tight">Clinical Diagnostic Worklist</h1>
          <p className="text-sm text-ink-500">
            Process physician diagnostic orders, record validated specimen findings, and update clinical records.
          </p>
        </div>
        <Button onClick={loadRequests} variant="secondary">
          <RefreshCw size={15} className={`mr-2 ${loading ? "animate-spin" : ""}`} />
          Refresh Worklist
        </Button>
      </div>

      {/* Metric Counters */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div
          onClick={() => setFilter("requested")}
          className={`cursor-pointer rounded-2xl border p-5 shadow-card transition ${
            filter === "requested" ? "border-amber-400 bg-amber-50/50" : "border-ink-100 bg-white hover:border-amber-200"
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-amber-800 uppercase tracking-wider">Pending Claim</span>
            <Clock size={18} className="text-amber-600" />
          </div>
          <p className="mt-3 text-3xl font-extrabold text-ink-900">{requestedCount}</p>
          <p className="mt-1 text-xs text-ink-500">Awaiting technician pickup</p>
        </div>

        <div
          onClick={() => setFilter("in_progress")}
          className={`cursor-pointer rounded-2xl border p-5 shadow-card transition ${
            filter === "in_progress" ? "border-blue-400 bg-blue-50/50" : "border-ink-100 bg-white hover:border-blue-200"
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-blue-800 uppercase tracking-wider">In Analysis</span>
            <FlaskConical size={18} className="text-blue-600" />
          </div>
          <p className="mt-3 text-3xl font-extrabold text-ink-900">{inProgressCount}</p>
          <p className="mt-1 text-xs text-ink-500">Specimens currently in testing</p>
        </div>

        <div
          onClick={() => setFilter("completed")}
          className={`cursor-pointer rounded-2xl border p-5 shadow-card transition ${
            filter === "completed" ? "border-emerald-400 bg-emerald-50/50" : "border-ink-100 bg-white hover:border-emerald-200"
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-emerald-800 uppercase tracking-wider">Completed</span>
            <CheckCircle2 size={18} className="text-emerald-600" />
          </div>
          <p className="mt-3 text-3xl font-extrabold text-ink-900">{completedCount}</p>
          <p className="mt-1 text-xs text-ink-500">Validated reports submitted</p>
        </div>
      </div>

      {/* Main Worklist Table */}
      <div className="rounded-2xl border border-ink-100 bg-white shadow-card overflow-hidden">
        {/* Table Controls */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-ink-100 p-5">
          <div className="flex items-center gap-2">
            <ClipboardList size={18} className="text-purple-700" />
            <h2 className="text-base font-bold text-ink-900">Diagnostic Orders Queue</h2>
          </div>

          <div className="flex items-center gap-1 bg-ink-50 p-1 rounded-lg self-start sm:self-auto">
            <button
              onClick={() => setFilter("all")}
              className={`px-3 py-1 text-xs font-semibold rounded-md transition ${
                filter === "all" ? "bg-white text-ink-900 shadow-sm" : "text-ink-500 hover:text-ink-900"
              }`}
            >
              All ({requests.length})
            </button>
            <button
              onClick={() => setFilter("requested")}
              className={`px-3 py-1 text-xs font-semibold rounded-md transition ${
                filter === "requested" ? "bg-white text-ink-900 shadow-sm" : "text-ink-500 hover:text-ink-900"
              }`}
            >
              Pending ({requestedCount})
            </button>
            <button
              onClick={() => setFilter("in_progress")}
              className={`px-3 py-1 text-xs font-semibold rounded-md transition ${
                filter === "in_progress" ? "bg-white text-ink-900 shadow-sm" : "text-ink-500 hover:text-ink-900"
              }`}
            >
              In Progress ({inProgressCount})
            </button>
            <button
              onClick={() => setFilter("completed")}
              className={`px-3 py-1 text-xs font-semibold rounded-md transition ${
                filter === "completed" ? "bg-white text-ink-900 shadow-sm" : "text-ink-500 hover:text-ink-900"
              }`}
            >
              Completed ({completedCount})
            </button>
          </div>
        </div>

        {error && (
          <div className="p-5 border-b border-red-100 bg-red-50 text-xs text-red-700">
            {error}
          </div>
        )}

        {loading ? (
          <div className="py-16 text-center text-xs text-ink-400">Loading diagnostic orders...</div>
        ) : filteredRequests.length === 0 ? (
          <div className="py-16 text-center text-xs text-ink-400">
            No diagnostic orders in this view.
          </div>
        ) : (
          <div className="divide-y divide-ink-100">
            {filteredRequests.map((req) => (
              <div
                key={req.id}
                className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-5 hover:bg-canvas/50 transition"
              >
                <div className="space-y-1.5">
                  <div className="flex items-center gap-2.5">
                    <span className="font-mono text-xs font-bold text-purple-900 bg-purple-50 px-2 py-0.5 rounded">
                      REQ #{req.id}
                    </span>
                    <h3 className="text-base font-bold text-ink-900">{req.test_name}</h3>
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                        req.priority === "stat"
                          ? "bg-red-50 text-red-700 border border-red-200"
                          : req.priority === "urgent"
                          ? "bg-amber-50 text-amber-700 border border-amber-200"
                          : "bg-ink-100 text-ink-600"
                      }`}
                    >
                      {req.priority}
                    </span>
                    <span
                      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                        req.status === "completed"
                          ? "bg-emerald-50 text-emerald-700"
                          : req.status === "in_progress"
                          ? "bg-blue-50 text-blue-700"
                          : "bg-amber-50 text-amber-700"
                      }`}
                    >
                      {req.status === "completed" && <CheckCircle2 size={11} />}
                      {req.status === "in_progress" && <FlaskConical size={11} />}
                      {req.status === "requested" && <Clock size={11} />}
                      {req.status.replace("_", " ")}
                    </span>
                  </div>

                  <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-ink-500">
                    <span className="flex items-center gap-1 font-medium text-ink-800">
                      <User size={13} /> {req.patient_name || `Patient #${req.patient}`}
                    </span>
                    <span className="flex items-center gap-1">
                      <Stethoscope size={13} /> Ordered by: {req.requested_by_name || "Doctor"}
                    </span>
                    {req.assigned_lab_tech_name && (
                      <span className="flex items-center gap-1">
                        <FlaskConical size={13} /> Tech: {req.assigned_lab_tech_name}
                      </span>
                    )}
                    <span className="text-ink-400 font-mono text-[11px]">
                      {new Date(req.created_at).toLocaleString()}
                    </span>
                  </div>

                  {req.notes && (
                    <p className="text-xs text-ink-600 italic bg-canvas p-2 rounded-lg inline-block">
                      Physician Note: "{req.notes}"
                    </p>
                  )}

                  {req.result && (
                    <div className="mt-2 rounded-xl border border-emerald-200 bg-emerald-50/50 p-3 text-xs space-y-1">
                      <p className="font-bold text-emerald-900 flex items-center gap-1.5">
                        <ShieldCheck size={14} className="text-emerald-600" />
                        Validated Laboratory Finding:
                      </p>
                      <p className="font-mono text-ink-900 bg-white p-2 rounded border border-emerald-100 font-semibold">
                        {req.result.result_text}
                      </p>
                      {req.result.notes && (
                        <p className="text-[11px] text-ink-500">
                          Technician Remarks: {req.result.notes}
                        </p>
                      )}
                    </div>
                  )}
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  {req.status === "requested" && (
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={() => handleClaim(req)}
                      className="bg-purple-700 hover:bg-purple-800 text-white"
                    >
                      <Play size={14} className="mr-1.5" />
                      Claim Specimen
                    </Button>
                  )}
                  {req.status === "in_progress" && (
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={() => openResultModal(req)}
                      className="bg-blue-600 hover:bg-blue-700 text-white"
                    >
                      <FileText size={14} className="mr-1.5" />
                      Enter Results
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Enter Lab Result Modal */}
      <Modal
        open={isResultModalOpen}
        onClose={() => setIsResultModalOpen(false)}
        title={`Record Lab Result: ${activeRequest?.test_name || ""}`}
      >
        <form onSubmit={handleSubmitResult} className="space-y-4">
          <div className="rounded-xl border border-ink-100 bg-canvas p-3 text-xs space-y-1">
            <p>
              <span className="font-bold">Patient:</span> {activeRequest?.patient_name} (ID #{activeRequest?.patient})
            </p>
            <p>
              <span className="font-bold">Ordering Physician:</span> {activeRequest?.requested_by_name}
            </p>
          </div>

          {resultError && (
            <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-xs text-red-700">
              {resultError}
            </div>
          )}

          <div className="space-y-1">
            <label className="text-xs font-semibold text-ink-700">
              Validated Test Finding / Numeric Value *
            </label>
            <textarea
              rows={3}
              placeholder="e.g. HbA1c: 7.8% (Elevated, Ref: 4.0 - 5.6%) or Glucose Fasting: 142 mg/dL"
              value={resultText}
              onChange={(e) => setResultText(e.target.value)}
              required
              className="w-full rounded-xl border border-ink-200 bg-white p-3 text-sm text-ink-900 focus:border-brand-500 focus:outline-none font-mono"
            />
          </div>

          <Input
            label="Technical Notes / Calibration / Machine Details (Optional)"
            placeholder="e.g. Automated analyzer Abbott Architect c4000, rerun and confirmed"
            value={resultNotes}
            onChange={(e) => setResultNotes(e.target.value)}
          />

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="ghost" onClick={() => setIsResultModalOpen(false)}>
              Cancel
            </Button>
            <Button
              type="submit"
              loading={submittingResult}
              className="bg-purple-700 hover:bg-purple-800 text-white"
            >
              <Send size={15} className="mr-1.5" />
              Submit Official Result
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
