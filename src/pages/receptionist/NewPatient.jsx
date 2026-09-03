import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { createPatient } from "../../api/reception.api";
import { confirmAppointment } from "../../api/appointment.api";

export default function NewPatient() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    name: "",
    age: "",
    gender: "Male",
    phone: "",
    email: "",
    assignedDoctor: "doc_1", // default demo doctor
  });

  const handleChange = (e) => {
    setFormData((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const patient = await createPatient({
        ...formData,
        age: parseInt(formData.age, 10)
      });
      
      // Auto check-in to link patient to doctor immediately
      await confirmAppointment({
        patientId: patient.id,
        doctorId: formData.assignedDoctor,
        doctorName: "Dr. Sarah Chen", // Mocked for simplicity
        date: new Date().toISOString(),
        time: "Now",
        reason: "Initial Visit",
      });
      
      alert("Patient created and checked in successfully!");
      navigate("/receptionist/dashboard");
    } catch (err) {
      alert("Error creating patient.");
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
        Back to Dashboard
      </button>

      <div>
        <h1 className="text-2xl font-bold text-ink-900">Register New Patient</h1>
        <p className="text-ink-500">Enter demographic details to create a new record.</p>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-ink-200 p-6">
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="grid grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-ink-700 mb-1">Full Name</label>
              <input required name="name" value={formData.name} onChange={handleChange} type="text" className="w-full p-2.5 border border-ink-300 rounded-lg outline-none focus:border-brand-500" />
            </div>
            <div>
              <label className="block text-sm font-medium text-ink-700 mb-1">Phone Number</label>
              <input required name="phone" value={formData.phone} onChange={handleChange} type="tel" className="w-full p-2.5 border border-ink-300 rounded-lg outline-none focus:border-brand-500" />
            </div>
            <div>
              <label className="block text-sm font-medium text-ink-700 mb-1">Age</label>
              <input required name="age" value={formData.age} onChange={handleChange} type="number" className="w-full p-2.5 border border-ink-300 rounded-lg outline-none focus:border-brand-500" />
            </div>
            <div>
              <label className="block text-sm font-medium text-ink-700 mb-1">Gender</label>
              <select name="gender" value={formData.gender} onChange={handleChange} className="w-full p-2.5 border border-ink-300 rounded-lg outline-none focus:border-brand-500 bg-white">
                <option value="Male">Male</option>
                <option value="Female">Female</option>
                <option value="Other">Other</option>
              </select>
            </div>
            <div className="col-span-2">
              <label className="block text-sm font-medium text-ink-700 mb-1">Email Address</label>
              <input required name="email" value={formData.email} onChange={handleChange} type="email" className="w-full p-2.5 border border-ink-300 rounded-lg outline-none focus:border-brand-500" />
            </div>
            <div className="col-span-2">
              <label className="block text-sm font-medium text-ink-700 mb-1">Assign Doctor</label>
              <select name="assignedDoctor" value={formData.assignedDoctor} onChange={handleChange} className="w-full p-2.5 border border-ink-300 rounded-lg outline-none focus:border-brand-500 bg-white">
                <option value="doc_1">Dr. Sarah Chen (Internal Medicine)</option>
              </select>
            </div>
          </div>
          
          <div className="pt-4 flex justify-end">
            <button 
              type="submit" 
              disabled={loading}
              className="bg-brand-600 text-white px-6 py-2.5 rounded-lg font-medium hover:bg-brand-700 disabled:opacity-50"
            >
              {loading ? "Registering..." : "Register Patient"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
