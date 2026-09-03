import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getLabQueue, updateLabTestStatus } from "../../api/lab.api";
import { ClipboardList, Play, CheckCircle } from "lucide-react";

export default function Queue() {
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  const fetchQueue = async () => {
    try {
      const data = await getLabQueue();
      // Filter out completed ones, or leave them for history. Let's filter out COMPLETED for the active queue
      setRequests(data.filter(r => r.status !== "COMPLETED"));
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQueue();
  }, []);

  const handleStatusChange = async (id, status) => {
    try {
      await updateLabTestStatus(id, status);
      fetchQueue();
    } catch (err) {
      alert("Failed to update status");
    }
  };

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-ink-900">Lab Queue</h1>
        <p className="text-ink-500">Manage pending and in-progress lab tests.</p>
      </div>

      {loading ? (
        <div className="text-center py-12 text-ink-500">Loading queue...</div>
      ) : requests.length === 0 ? (
        <div className="bg-white rounded-xl shadow-sm border border-ink-200 p-12 text-center text-ink-500">
          <ClipboardList className="mx-auto h-12 w-12 text-ink-300 mb-4" />
          <p className="text-lg font-medium text-ink-900 mb-1">Queue is empty</p>
          <p>No pending lab requests right now.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {requests.map(req => (
            <div key={req.id} className="bg-white rounded-xl shadow-sm border border-ink-200 p-5 flex items-center justify-between">
              <div>
                <div className="flex items-center gap-3 mb-1">
                  <h3 className="font-bold text-ink-900 text-lg">{req.testType}</h3>
                  <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                    req.status === 'REQUESTED' ? 'bg-amber-100 text-amber-800' :
                    req.status === 'IN_PROGRESS' ? 'bg-blue-100 text-blue-800' :
                    'bg-gray-100 text-gray-800'
                  }`}>
                    {req.status}
                  </span>
                </div>
                <p className="text-sm text-ink-500">
                  Patient: {req.patientName} (ID: {req.patientId})<br/>
                  Requested by: {req.doctorName}
                </p>
                <p className="text-xs text-ink-400 mt-2">
                  Expected by: {req.expectedBy || "ASAP"}
                </p>
              </div>

              <div className="flex items-center gap-3">
                {req.status === "REQUESTED" && (
                  <button
                    onClick={() => handleStatusChange(req.id, "IN_PROGRESS")}
                    className="flex items-center gap-2 bg-brand-50 text-brand-700 border border-brand-200 px-4 py-2 rounded-lg font-medium hover:bg-brand-100 transition"
                  >
                    <Play size={16} />
                    Start Processing
                  </button>
                )}
                {req.status === "IN_PROGRESS" && (
                  <button
                    onClick={() => navigate(`/lab/test/${req.id}`)}
                    className="flex items-center gap-2 bg-brand-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-brand-700 transition"
                  >
                    <CheckCircle size={16} />
                    Enter Results
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
