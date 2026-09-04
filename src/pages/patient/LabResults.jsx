import React, { useEffect, useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { getLabResultsForPatient } from "../../api/lab.api";
import EmptyState from "../../components/ui/EmptyState";
import { FileText, CheckCircle, Clock } from "lucide-react";

// Maps a raw backend LabTestRequest (with its nested `result`) onto the
// shape this page renders. A result is only shown to the patient once the
// doctor has reviewed it (result.reviewed_at set) - matches the backend's
// intended "doctor reviews, then patient sees" flow
// (LabTestResultReviewView). The AI Engine's reference-range read
// (result.ai_status/ai_explanation - see apps.labtests.ai_client) is
// surfaced as a single synthetic value row, since this build stores one
// result_text per test rather than itemized panel values.
function mapLabRequestToDisplay(req) {
  const result = req.result;
  const released = Boolean(result?.reviewed_at);
  const values = [];
  if (result?.ai_status) {
    values.push({
      name: req.test_name,
      value: result.ai_numeric_value != null ? result.ai_numeric_value : result.ai_status,
      unit: result.ai_numeric_value != null ? result.ai_unit : "",
      flag: result.ai_status,
      referenceRange: result.ai_reference_range || "",
    });
  }
  return {
    id: req.id,
    testType: req.test_name,
    date: req.created_at,
    releaseStatus: released ? "RELEASED" : "PENDING",
    values,
    resultText: result?.result_text,
    aiAnalysis: result?.ai_explanation,
  };
}

export default function LabResults() {
  const { user } = useAuth();
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getLabResultsForPatient(user.id)
      .then((data) => setResults(data.map(mapLabRequestToDisplay)))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [user.id]);

  return (
    <div className="flex-1 px-5 pb-6 pt-8">
      <h1 className="text-lg font-semibold text-ink-900">Lab Results</h1>
      <p className="mt-1 text-sm text-ink-500">Review your test results and health indicators.</p>

      {loading ? (
        <div className="py-12 text-center text-ink-500">Loading...</div>
      ) : results.length === 0 ? (
        <div className="mt-6">
          <EmptyState title="No lab results" description="You have no recent lab tests." />
        </div>
      ) : (
        <div className="mt-6 space-y-4">
          {results.map((res) => (
            <div key={res.id} className="bg-white rounded-xl shadow-sm border border-ink-200 p-5">
              <div className="flex justify-between items-start mb-4">
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 bg-brand-50 rounded-full flex items-center justify-center text-brand-600">
                    <FileText size={20} />
                  </div>
                  <div>
                    <h3 className="font-bold text-ink-900">{res.testType}</h3>
                    <p className="text-xs text-ink-500">{new Date(res.date).toLocaleDateString()}</p>
                  </div>
                </div>
                
                {res.releaseStatus === "RELEASED" ? (
                  <span className="flex items-center gap-1 text-xs font-semibold text-green-700 bg-green-50 px-2.5 py-1 rounded-full">
                    <CheckCircle size={14} /> Released
                  </span>
                ) : (
                  <span className="flex items-center gap-1 text-xs font-semibold text-amber-700 bg-amber-50 px-2.5 py-1 rounded-full">
                    <Clock size={14} /> Doctor Reviewing
                  </span>
                )}
              </div>

              {res.releaseStatus === "RELEASED" ? (
                <div className="space-y-3 border-t border-ink-100 pt-4">
                  {res.resultText && (
                    <div className="bg-canvas-soft p-3 rounded-lg border border-ink-100 text-sm text-ink-800 whitespace-pre-wrap">
                      {res.resultText}
                    </div>
                  )}
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
              ) : (
                <div className="text-sm text-ink-500 italic border-t border-ink-100 pt-4">
                  This result is currently being reviewed by your doctor and will be available shortly.
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
