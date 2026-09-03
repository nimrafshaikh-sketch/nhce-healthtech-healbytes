import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Search, UserPlus, Calendar } from "lucide-react";
import { searchPatient, createAppointment } from "../../api/reception.api";
import { confirmAppointment } from "../../api/appointment.api";

export default function Dashboard() {
  const [query, setQuery] = useState("");
  const [patients, setPatients] = useState([]);
  const [searching, setSearching] = useState(false);
  const navigate = useNavigate();

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;
    setSearching(true);
    try {
      const results = await searchPatient(query);
      setPatients(results);
    } catch (err) {
      console.error(err);
    } finally {
      setSearching(false);
    }
  };

  const handleCreateAppointment = async (patientId) => {
    try {
      await confirmAppointment({
        patientId,
        doctorId: "doc_1", 
        doctorName: "Dr. Sarah Chen",
        date: new Date().toISOString(),
        time: "Now",
        reason: "Walk-in",
      });
      alert("Appointment created successfully! Patient linked to doctor.");
    } catch (err) {
      alert("Failed to create appointment.");
    }
  };

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-ink-900">Patient Search</h1>
          <p className="text-ink-500">Find existing patients or register new arrivals.</p>
        </div>
        <button
          onClick={() => navigate("/receptionist/patients/new")}
          className="flex items-center gap-2 bg-brand-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-brand-700 transition"
        >
          <UserPlus size={18} />
          New Patient
        </button>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-ink-200 p-6">
        <form onSubmit={handleSearch} className="flex gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-ink-400" size={20} />
            <input
              type="text"
              placeholder="Search by phone, name, or ID..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="w-full pl-12 pr-4 py-3 rounded-lg border border-ink-300 focus:ring-2 focus:ring-brand-500 outline-none"
            />
          </div>
          <button
            type="submit"
            disabled={searching}
            className="bg-ink-900 text-white px-6 py-3 rounded-lg font-medium hover:bg-ink-800 disabled:opacity-50"
          >
            {searching ? "Searching..." : "Search"}
          </button>
        </form>
      </div>

      <div className="space-y-4">
        {patients.length === 0 && query && !searching && (
          <div className="text-center py-12 text-ink-500 bg-white rounded-xl border border-ink-200">
            No patients found matching "{query}".
          </div>
        )}
        
        {patients.map((patient) => (
          <div key={patient.id} className="bg-white rounded-xl shadow-sm border border-ink-200 p-5 flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="h-12 w-12 rounded-full bg-brand-100 text-brand-700 flex items-center justify-center font-bold text-lg">
                {patient.avatarInitials}
              </div>
              <div>
                <h3 className="font-bold text-ink-900 text-lg">{patient.name}</h3>
                <p className="text-sm text-ink-500 flex gap-4">
                  <span>ID: {patient.id}</span>
                  <span>{patient.gender} • {patient.age} yrs</span>
                  <span>{patient.phone}</span>
                </p>
              </div>
            </div>
            
            <button
              onClick={() => handleCreateAppointment(patient.id)}
              className="flex items-center gap-2 bg-brand-50 text-brand-700 border border-brand-200 px-4 py-2 rounded-lg font-medium hover:bg-brand-100 transition"
            >
              <Calendar size={18} />
              Check In
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
