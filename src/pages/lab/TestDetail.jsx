import React, { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeft, Upload } from "lucide-react";
import { submitLabResult } from "../../api/lab.api";

export default function TestDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [file, setFile] = useState(null);

  // In a real app, you would fetch the request details by ID to know which fields to show.
  // For the demo, we'll provide a generic form to enter values.
  const [values, setValues] = useState([
    { name: "", value: "", unit: "", referenceRange: "", flag: "NORMAL" }
  ]);

  const addValue = () => {
    setValues([...values, { name: "", value: "", unit: "", referenceRange: "", flag: "NORMAL" }]);
  };

  const updateValue = (index, field, val) => {
    const newValues = [...values];
    newValues[index][field] = val;
    setValues(newValues);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      // In a real implementation, if a file is attached, it would be uploaded as a document
      // and linked to this result. For this mock, we just submit the structured values.
      const validValues = values.filter(v => v.name && v.value);
      await submitLabResult(id, { values: validValues });
      alert("Results submitted successfully!");
      navigate("/lab/queue");
    } catch (err) {
      alert("Failed to submit results.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-8 max-w-3xl mx-auto space-y-8">
      <button 
        onClick={() => navigate(-1)}
        className="flex items-center gap-2 text-ink-500 hover:text-ink-900 transition-colors"
      >
        <ArrowLeft size={18} />
        Back to Queue
      </button>

      <div>
        <h1 className="text-2xl font-bold text-ink-900">Enter Lab Results</h1>
        <p className="text-ink-500">Request ID: {id}</p>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-ink-200 p-6">
        <form onSubmit={handleSubmit} className="space-y-6">
          
          <div>
            <h3 className="text-sm font-bold text-ink-900 mb-4 border-b border-ink-100 pb-2">Structured Results</h3>
            <div className="space-y-3">
              {values.map((v, i) => (
                <div key={i} className="flex items-start gap-3">
                  <input
                    type="text"
                    placeholder="Test Item (e.g. LDL)"
                    value={v.name}
                    onChange={(e) => updateValue(i, 'name', e.target.value)}
                    className="flex-1 p-2 border border-ink-300 rounded outline-none focus:border-brand-500 text-sm"
                  />
                  <input
                    type="text"
                    placeholder="Value"
                    value={v.value}
                    onChange={(e) => updateValue(i, 'value', e.target.value)}
                    className="w-24 p-2 border border-ink-300 rounded outline-none focus:border-brand-500 text-sm"
                  />
                  <input
                    type="text"
                    placeholder="Unit"
                    value={v.unit}
                    onChange={(e) => updateValue(i, 'unit', e.target.value)}
                    className="w-24 p-2 border border-ink-300 rounded outline-none focus:border-brand-500 text-sm"
                  />
                  <input
                    type="text"
                    placeholder="Ref. Range"
                    value={v.referenceRange}
                    onChange={(e) => updateValue(i, 'referenceRange', e.target.value)}
                    className="flex-1 p-2 border border-ink-300 rounded outline-none focus:border-brand-500 text-sm"
                  />
                  <select
                    value={v.flag}
                    onChange={(e) => updateValue(i, 'flag', e.target.value)}
                    className="w-28 p-2 border border-ink-300 rounded outline-none focus:border-brand-500 text-sm bg-white"
                  >
                    <option value="NORMAL">Normal</option>
                    <option value="HIGH">High</option>
                    <option value="LOW">Low</option>
                  </select>
                </div>
              ))}
            </div>
            <button
              type="button"
              onClick={addValue}
              className="mt-3 text-sm font-medium text-brand-600 hover:text-brand-700"
            >
              + Add Item
            </button>
          </div>

          <div>
            <h3 className="text-sm font-bold text-ink-900 mb-4 border-b border-ink-100 pb-2">Attach Original Report (Optional)</h3>
            <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-ink-300 border-dashed rounded-lg cursor-pointer bg-ink-50 hover:bg-ink-100 transition">
              <div className="flex flex-col items-center justify-center pt-5 pb-6">
                <Upload className="w-8 h-8 mb-2 text-ink-400" />
                <p className="text-sm text-ink-500 font-medium">
                  {file ? file.name : "Click to upload file"}
                </p>
              </div>
              <input type="file" className="hidden" onChange={(e) => setFile(e.target.files[0])} />
            </label>
          </div>

          <div className="pt-4 flex justify-end">
            <button
              type="submit"
              disabled={loading}
              className="bg-brand-600 text-white px-6 py-2.5 rounded-lg font-medium hover:bg-brand-700 disabled:opacity-50"
            >
              {loading ? "Submitting..." : "Submit Results"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
