// NOT ROUTED/IMPORTED ANYWHERE - kept for reference, not wired into any
// page. Its premise (a patient picks an open time slot and self-books) has
// no backend support: there is no "available slots" endpoint, and patients
// are explicitly forbidden from creating appointments at all (only
// Doctor/Receptionist can POST /appointments/ - see
// backend/apps/appointments/views.py::AppointmentListCreateView.get_permissions,
// backend/apps/appointments/tests/test_appointments.py::test_patient_cannot_book_appointment).
// A patient can only view their own appointments and confirm/cancel an
// already-scheduled one - see pages/patient/Appointments.jsx and
// api/appointment.api.js::getMyAppointments/confirmAppointment/cancelAppointment
// for the real, working implementation of that.
import React, { useState, useEffect } from "react";
import { Calendar, CheckCircle } from "lucide-react";
import { getAvailableSlots, confirmAppointment } from "../../api/appointment.api";

export default function AppointmentFollowUp({ patientId, doctorId }) {
  const [slots, setSlots] = useState([]);
  const [selectedSlot, setSelectedSlot] = useState(null);
  const [loading, setLoading] = useState(true);
  const [confirming, setConfirming] = useState(false);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    const today = new Date().toISOString().split("T")[0];
    getAvailableSlots(doctorId, today)
      .then(setSlots)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [doctorId]);

  const handleConfirm = async () => {
    if (!selectedSlot) return;
    setConfirming(true);
    try {
      await confirmAppointment({
        patientId,
        doctorId,
        date: new Date().toISOString().split("T")[0],
        time: selectedSlot,
        reason: "Follow-up",
      });
      setSuccess(true);
    } catch (err) {
      alert("Failed to confirm appointment");
    } finally {
      setConfirming(false);
    }
  };

  if (loading) return <div className="text-sm text-ink-500">Checking availability...</div>;

  if (success) return (
    <div className="flex items-center gap-3 p-4 bg-green-50 text-green-800 rounded-xl border border-green-200">
      <CheckCircle size={24} />
      <div>
        <h4 className="font-bold">Appointment Confirmed</h4>
        <p className="text-sm">We'll see you at {selectedSlot}.</p>
      </div>
    </div>
  );

  return (
    <div className="p-4 bg-white rounded-xl shadow-sm border border-ink-200">
      <h4 className="font-bold text-ink-900 mb-1 flex items-center gap-2">
        <Calendar size={18} className="text-brand-600" />
        Schedule Follow-up
      </h4>
      <p className="text-xs text-ink-500 mb-4">Select a convenient time for your follow-up visit.</p>
      
      <div className="flex flex-wrap gap-2 mb-4">
        {slots.map(slot => (
          <button
            key={slot}
            onClick={() => setSelectedSlot(slot)}
            className={`px-3 py-1.5 text-sm rounded-lg border transition ${
              selectedSlot === slot 
                ? "bg-brand-600 border-brand-600 text-white" 
                : "bg-white border-ink-300 text-ink-700 hover:border-brand-400"
            }`}
          >
            {slot}
          </button>
        ))}
      </div>

      <button
        onClick={handleConfirm}
        disabled={!selectedSlot || confirming}
        className="w-full bg-brand-600 text-white py-2 rounded-lg font-medium text-sm hover:bg-brand-700 disabled:opacity-50"
      >
        {confirming ? "Confirming..." : "Confirm Appointment"}
      </button>
    </div>
  );
}
