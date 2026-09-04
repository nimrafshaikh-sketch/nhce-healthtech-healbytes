import React, { useState, useEffect } from "react";
import {
  Search,
  UserPlus,
  Calendar,
  KeyRound,
  CheckCircle2,
  Clock,
  User,
  Phone,
  CalendarDays,
  ShieldCheck,
  Stethoscope,
  RefreshCw,
} from "lucide-react";
import Button from "../../components/ui/Button";
import Input from "../../components/ui/Input";
import Modal from "../../components/ui/Modal";
import {
  searchPatients,
  createReceptionistPatient,
  getDoctorsList,
  getAppointments,
  bookAppointment,
  generatePatientInvitation,
} from "../../api/receptionist.api";

export default function ReceptionistDashboard() {
  // Search State
  const [searchType, setSearchType] = useState("phone"); // 'phone' | 'namedob'
  const [searchPhone, setSearchPhone] = useState("");
  const [searchName, setSearchName] = useState("");
  const [searchDob, setSearchDob] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchError, setSearchError] = useState(null);
  const [hasSearched, setHasSearched] = useState(false);

  // Doctors & Appointments State
  const [doctors, setDoctors] = useState([]);
  const [appointments, setAppointments] = useState([]);
  const [loadingAppointments, setLoadingAppointments] = useState(false);

  // Selected Patient for Actions
  const [selectedPatient, setSelectedPatient] = useState(null);

  // Modals State
  const [isRegisterOpen, setIsRegisterOpen] = useState(false);
  const [isBookOpen, setIsBookOpen] = useState(false);
  const [isInviteOpen, setIsInviteOpen] = useState(false);
  const [invitationCode, setInvitationCode] = useState(null);

  // Form States
  const [newPatientData, setNewPatientData] = useState({
    doctor: "",
    full_name: "",
    date_of_birth: "",
    gender: "MALE",
    phone_number: "",
    address: "",
    caretaker_name: "",
    caretaker_relationship: "",
    caretaker_phone_number: "",
    caretaker_email: "",
  });
  const [registerLoading, setRegisterLoading] = useState(false);
  const [registerError, setRegisterError] = useState(null);

  const [bookingData, setBookingData] = useState({
    doctorId: "",
    scheduledAt: "",
    durationMinutes: 30,
    reason: "",
    notes: "",
  });
  const [bookingLoading, setBookingLoading] = useState(false);
  const [bookingSuccess, setBookingSuccess] = useState(false);
  const [bookingError, setBookingError] = useState(null);

  useEffect(() => {
    loadDoctors();
    loadAppointments();
  }, []);

  async function loadDoctors() {
    try {
      const res = await getDoctorsList();
      const list = Array.isArray(res) ? res : res.results || [];
      setDoctors(list);
      if (list.length > 0) {
        setNewPatientData((prev) => ({ ...prev, doctor: list[0].id }));
        setBookingData((prev) => ({ ...prev, doctorId: list[0].id }));
      }
    } catch (err) {
      console.error("Failed to load doctors", err);
    }
  }

  async function loadAppointments() {
    setLoadingAppointments(true);
    try {
      const res = await getAppointments();
      setAppointments(Array.isArray(res) ? res : res.results || []);
    } catch (err) {
      console.error("Failed to load appointments", err);
    } finally {
      setLoadingAppointments(false);
    }
  }

  async function handleSearch(e) {
    if (e) e.preventDefault();
    setSearchLoading(true);
    setSearchError(null);
    setHasSearched(true);
    try {
      const query =
        searchType === "phone"
          ? { phone: searchPhone.trim() }
          : { name: searchName.trim(), dob: searchDob.trim() };
      const res = await searchPatients(query);
      const results = Array.isArray(res) ? res : res.results || [];
      setSearchResults(results);
    } catch (err) {
      setSearchError(err.message || "Failed to search patient records.");
      setSearchResults([]);
    } finally {
      setSearchLoading(false);
    }
  }

  async function handleRegister(e) {
    e.preventDefault();
    setRegisterLoading(true);
    setRegisterError(null);
    try {
      const created = await createReceptionistPatient(newPatientData);
      setIsRegisterOpen(false);
      setSearchResults([created]);
      setSelectedPatient(created);
      setHasSearched(true);
      setNewPatientData({
        doctor: doctors[0]?.id || "",
        full_name: "",
        date_of_birth: "",
        gender: "MALE",
        phone_number: "",
        address: "",
        caretaker_name: "",
        caretaker_relationship: "",
        caretaker_phone_number: "",
        caretaker_email: "",
      });
    } catch (err) {
      setRegisterError(err.message || "Failed to register patient.");
    } finally {
      setRegisterLoading(false);
    }
  }

  async function handleBookAppointment(e) {
    e.preventDefault();
    if (!selectedPatient) return;
    setBookingLoading(true);
    setBookingError(null);
    try {
      await bookAppointment({
        patientId: selectedPatient.id,
        doctorId: bookingData.doctorId || selectedPatient.doctor || doctors[0]?.id,
        scheduledAt: bookingData.scheduledAt,
        durationMinutes: bookingData.durationMinutes,
        reason: bookingData.reason,
        notes: bookingData.notes,
      });
      setBookingSuccess(true);
      loadAppointments();
      setTimeout(() => {
        setIsBookOpen(false);
        setBookingSuccess(false);
        setBookingData({
          doctorId: doctors[0]?.id || "",
          scheduledAt: "",
          durationMinutes: 30,
          reason: "",
          notes: "",
        });
      }, 1200);
    } catch (err) {
      setBookingError(err.message || "Failed to schedule appointment.");
    } finally {
      setBookingLoading(false);
    }
  }

  async function handleGenerateInvitation(patient) {
    setSelectedPatient(patient);
    setIsInviteOpen(true);
    setInvitationCode(null);
    try {
      const res = await generatePatientInvitation(patient.id);
      setInvitationCode(res.code);
    } catch (err) {
      setInvitationCode("ERR: " + (err.message || "Failed to generate"));
    }
  }

  function openBookingModal(patient) {
    setSelectedPatient(patient);
    setBookingData((prev) => ({
      ...prev,
      doctorId: patient.doctor || doctors[0]?.id || "",
    }));
    setIsBookOpen(true);
  }

  return (
    <div className="space-y-8">
      {/* Header Banner */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-ink-900 tracking-tight">Patient Reception & Registration</h1>
          <p className="text-sm text-ink-500">
            Search authoritative patient records, book clinic appointments, or register new patients.
          </p>
        </div>
        <Button onClick={() => setIsRegisterOpen(true)} className="self-start sm:self-auto">
          <UserPlus size={16} className="mr-2" />
          Register New Patient
        </Button>
      </div>

      {/* Main Grid: Search & Registration on Left, Today's Schedule on Right */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left 2 Cols: Search & Results */}
        <div className="lg:col-span-2 space-y-6">
          {/* Patient Lookup Card */}
          <div className="rounded-2xl border border-ink-100 bg-white p-6 shadow-card">
            <div className="flex items-center justify-between border-b border-ink-100 pb-4 mb-5">
              <h2 className="text-base font-bold text-ink-900 flex items-center gap-2">
                <Search size={18} className="text-brand-700" />
                Find Patient Record
              </h2>
              <div className="flex items-center gap-1 bg-ink-50 p-1 rounded-lg">
                <button
                  type="button"
                  onClick={() => setSearchType("phone")}
                  className={`px-3 py-1 text-xs font-semibold rounded-md transition ${
                    searchType === "phone" ? "bg-white text-ink-900 shadow-sm" : "text-ink-500 hover:text-ink-900"
                  }`}
                >
                  By Phone
                </button>
                <button
                  type="button"
                  onClick={() => setSearchType("namedob")}
                  className={`px-3 py-1 text-xs font-semibold rounded-md transition ${
                    searchType === "namedob" ? "bg-white text-ink-900 shadow-sm" : "text-ink-500 hover:text-ink-900"
                  }`}
                >
                  By Name & DOB
                </button>
              </div>
            </div>

            <form onSubmit={handleSearch} className="space-y-4">
              {searchType === "phone" ? (
                <div className="flex gap-3">
                  <div className="flex-1">
                    <Input
                      placeholder="Enter patient phone number (e.g. +1-555-0199)"
                      value={searchPhone}
                      onChange={(e) => setSearchPhone(e.target.value)}
                      required
                    />
                  </div>
                  <Button type="submit" loading={searchLoading}>
                    <Search size={16} className="mr-1.5" /> Search
                  </Button>
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <Input
                    label="Patient Full Name"
                    placeholder="e.g. Eleanor Vance"
                    value={searchName}
                    onChange={(e) => setSearchName(e.target.value)}
                    required
                  />
                  <Input
                    label="Date of Birth"
                    type="date"
                    value={searchDob}
                    onChange={(e) => setSearchDob(e.target.value)}
                    required
                  />
                  <div className="sm:col-span-2 flex justify-end">
                    <Button type="submit" loading={searchLoading}>
                      <Search size={16} className="mr-1.5" /> Search Patient
                    </Button>
                  </div>
                </div>
              )}
            </form>

            {searchError && (
              <div className="mt-4 rounded-xl border border-red-200 bg-red-50 p-3 text-xs text-red-700">
                {searchError}
              </div>
            )}
          </div>

          {/* Search Results Area */}
          {hasSearched && (
            <div className="space-y-4">
              <h3 className="text-sm font-bold text-ink-700">
                Search Results ({searchResults.length})
              </h3>

              {searchResults.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-ink-200 bg-white p-8 text-center">
                  <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-canvas-soft text-ink-400">
                    <User size={24} />
                  </div>
                  <p className="mt-3 text-sm font-semibold text-ink-800">No Patient Record Found</p>
                  <p className="mt-1 text-xs text-ink-400 max-w-sm mx-auto">
                    No existing patient matches this query. You can register them as a new patient.
                  </p>
                  <Button onClick={() => setIsRegisterOpen(true)} size="sm" className="mt-4">
                    <UserPlus size={14} className="mr-1.5" /> Register This Patient
                  </Button>
                </div>
              ) : (
                <div className="space-y-3">
                  {searchResults.map((patient) => (
                    <div
                      key={patient.id}
                      className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 rounded-2xl border border-ink-100 bg-white p-5 shadow-card hover:border-brand-200 transition"
                    >
                      <div className="space-y-1">
                        <div className="flex items-center gap-2.5">
                          <span className="inline-flex items-center justify-center px-2 py-0.5 rounded bg-brand-50 text-[11px] font-mono font-bold text-brand-800">
                            Patient #{patient.id}
                          </span>
                          <h4 className="text-base font-bold text-ink-900">{patient.full_name}</h4>
                          {patient.is_linked ? (
                            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold text-emerald-700">
                              <ShieldCheck size={12} /> App Active
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-semibold text-amber-700">
                              <Clock size={12} /> Pending Activation
                            </span>
                          )}
                        </div>

                        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-ink-500 pt-1">
                          <span className="flex items-center gap-1">
                            <Phone size={13} /> {patient.phone_number}
                          </span>
                          <span className="flex items-center gap-1">
                            <CalendarDays size={13} /> DOB: {patient.date_of_birth}
                          </span>
                          <span className="flex items-center gap-1">
                            <Stethoscope size={13} /> Doctor: {patient.doctor_name || `Doctor #${patient.doctor}`}
                          </span>
                        </div>
                      </div>

                      <div className="flex items-center gap-2 shrink-0">
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => handleGenerateInvitation(patient)}
                        >
                          <KeyRound size={14} className="mr-1" />
                          Invite Code
                        </Button>
                        <Button
                          variant="primary"
                          size="sm"
                          onClick={() => openBookingModal(patient)}
                        >
                          <Calendar size={14} className="mr-1" />
                          Book Visit
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Right Col: Clinic Appointments List */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-ink-900 flex items-center gap-2">
              <Calendar size={18} className="text-brand-700" />
              Clinic Appointments
            </h2>
            <button
              onClick={loadAppointments}
              className="text-xs text-brand-700 hover:underline flex items-center gap-1 font-semibold"
            >
              <RefreshCw size={12} className={loadingAppointments ? "animate-spin" : ""} /> Refresh
            </button>
          </div>

          <div className="rounded-2xl border border-ink-100 bg-white p-4 shadow-card space-y-3">
            {loadingAppointments ? (
              <div className="py-8 text-center text-xs text-ink-400">Loading appointments...</div>
            ) : appointments.length === 0 ? (
              <div className="py-8 text-center text-xs text-ink-400">No scheduled appointments found.</div>
            ) : (
              appointments.slice(0, 10).map((apt) => (
                <div
                  key={apt.id}
                  className="rounded-xl border border-ink-100 bg-canvas p-3 text-xs space-y-1"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-ink-900">{apt.patient_name || `Patient #${apt.patient}`}</span>
                    <span className="rounded bg-brand-50 px-1.5 py-0.5 text-[10px] font-semibold text-brand-800">
                      {apt.status}
                    </span>
                  </div>
                  <p className="text-ink-600">
                    <span className="font-medium">With:</span> {apt.doctor_name || `Doctor #${apt.doctor}`}
                  </p>
                  <p className="text-ink-400 font-mono text-[11px]">
                    {new Date(apt.scheduled_at).toLocaleString()}
                  </p>
                  {apt.reason && (
                    <p className="text-ink-500 italic text-[11px]">"{apt.reason}"</p>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* MODAL 1: Register New Patient */}
      <Modal
        open={isRegisterOpen}
        onClose={() => setIsRegisterOpen(false)}
        title="Register New Patient Record"
      >
        <form onSubmit={handleRegister} className="space-y-4">
          {registerError && (
            <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-xs text-red-700">
              {registerError}
            </div>
          )}

          <div className="space-y-1">
            <label className="text-xs font-semibold text-ink-700">Assigned Primary Doctor</label>
            <select
              value={newPatientData.doctor}
              onChange={(e) => setNewPatientData({ ...newPatientData, doctor: e.target.value })}
              required
              className="w-full rounded-xl border border-ink-200 bg-white px-3 py-2 text-sm text-ink-900 focus:border-brand-500 focus:outline-none"
            >
              {doctors.map((doc) => (
                <option key={doc.id} value={doc.id}>
                  Dr. {doc.first_name} {doc.last_name} ({doc.specialization || "General Practice"})
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <Input
              label="Full Name"
              placeholder="e.g. John Doe"
              value={newPatientData.full_name}
              onChange={(e) => setNewPatientData({ ...newPatientData, full_name: e.target.value })}
              required
            />
            <Input
              label="Date of Birth"
              type="date"
              value={newPatientData.date_of_birth}
              onChange={(e) => setNewPatientData({ ...newPatientData, date_of_birth: e.target.value })}
              required
            />
            <div className="space-y-1">
              <label className="text-xs font-semibold text-ink-700">Gender</label>
              <select
                value={newPatientData.gender}
                onChange={(e) => setNewPatientData({ ...newPatientData, gender: e.target.value })}
                className="w-full rounded-xl border border-ink-200 bg-white px-3 py-2 text-sm text-ink-900 focus:border-brand-500 focus:outline-none"
              >
                <option value="MALE">Male</option>
                <option value="FEMALE">Female</option>
                <option value="OTHER">Other</option>
              </select>
            </div>
            <Input
              label="Phone Number"
              placeholder="+1-555-0100"
              value={newPatientData.phone_number}
              onChange={(e) => setNewPatientData({ ...newPatientData, phone_number: e.target.value })}
              required
            />
          </div>

          <Input
            label="Residential Address"
            placeholder="123 Healthway St, Suite 4"
            value={newPatientData.address}
            onChange={(e) => setNewPatientData({ ...newPatientData, address: e.target.value })}
          />

          <div className="border-t border-ink-100 pt-3">
            <p className="text-xs font-bold text-ink-700 mb-2">Caretaker / Emergency Contact (Optional)</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <Input
                label="Caretaker Name"
                placeholder="e.g. Jane Doe"
                value={newPatientData.caretaker_name}
                onChange={(e) => setNewPatientData({ ...newPatientData, caretaker_name: e.target.value })}
              />
              <Input
                label="Relationship"
                placeholder="e.g. Spouse / Daughter"
                value={newPatientData.caretaker_relationship}
                onChange={(e) => setNewPatientData({ ...newPatientData, caretaker_relationship: e.target.value })}
              />
              <Input
                label="Caretaker Phone"
                placeholder="+1-555-0101"
                value={newPatientData.caretaker_phone_number}
                onChange={(e) => setNewPatientData({ ...newPatientData, caretaker_phone_number: e.target.value })}
              />
              <Input
                label="Caretaker Email"
                placeholder="caretaker@example.com"
                value={newPatientData.caretaker_email}
                onChange={(e) => setNewPatientData({ ...newPatientData, caretaker_email: e.target.value })}
              />
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="ghost" onClick={() => setIsRegisterOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" loading={registerLoading}>
              Create Patient Record
            </Button>
          </div>
        </form>
      </Modal>

      {/* MODAL 2: Book Clinic Appointment */}
      <Modal
        open={isBookOpen}
        onClose={() => setIsBookOpen(false)}
        title={`Book Appointment: ${selectedPatient?.full_name || ""}`}
      >
        <form onSubmit={handleBookAppointment} className="space-y-4">
          {bookingSuccess ? (
            <div className="py-6 text-center text-emerald-600 space-y-2">
              <CheckCircle2 size={36} className="mx-auto" />
              <p className="text-base font-bold text-ink-900">Appointment Confirmed!</p>
              <p className="text-xs text-ink-500">Scheduled successfully in the clinic database.</p>
            </div>
          ) : (
            <>
              {bookingError && (
                <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-xs text-red-700">
                  {bookingError}
                </div>
              )}

              <div className="space-y-1">
                <label className="text-xs font-semibold text-ink-700">Consulting Doctor</label>
                <select
                  value={bookingData.doctorId}
                  onChange={(e) => setBookingData({ ...bookingData, doctorId: e.target.value })}
                  required
                  className="w-full rounded-xl border border-ink-200 bg-white px-3 py-2 text-sm text-ink-900 focus:border-brand-500 focus:outline-none"
                >
                  {doctors.map((doc) => (
                    <option key={doc.id} value={doc.id}>
                      Dr. {doc.first_name} {doc.last_name} ({doc.specialization || "General Practice"})
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <Input
                  label="Appointment Date & Time"
                  type="datetime-local"
                  value={bookingData.scheduledAt}
                  onChange={(e) => setBookingData({ ...bookingData, scheduledAt: e.target.value })}
                  required
                />
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-ink-700">Duration (Minutes)</label>
                  <select
                    value={bookingData.durationMinutes}
                    onChange={(e) => setBookingData({ ...bookingData, durationMinutes: e.target.value })}
                    className="w-full rounded-xl border border-ink-200 bg-white px-3 py-2 text-sm text-ink-900 focus:border-brand-500 focus:outline-none"
                  >
                    <option value={15}>15 mins</option>
                    <option value={30}>30 mins</option>
                    <option value={45}>45 mins</option>
                    <option value={60}>60 mins</option>
                  </select>
                </div>
              </div>

              <Input
                label="Reason for Visit"
                placeholder="e.g. Routine follow-up / Blood pressure review"
                value={bookingData.reason}
                onChange={(e) => setBookingData({ ...bookingData, reason: e.target.value })}
                required
              />

              <Input
                label="Administrative Notes (Optional)"
                placeholder="e.g. Patient requests morning slot"
                value={bookingData.notes}
                onChange={(e) => setBookingData({ ...bookingData, notes: e.target.value })}
              />

              <div className="flex justify-end gap-2 pt-2">
                <Button type="button" variant="ghost" onClick={() => setIsBookOpen(false)}>
                  Cancel
                </Button>
                <Button type="submit" loading={bookingLoading}>
                  Confirm Appointment
                </Button>
              </div>
            </>
          )}
        </form>
      </Modal>

      {/* MODAL 3: Invitation Code Display */}
      <Modal
        open={isInviteOpen}
        onClose={() => setIsInviteOpen(false)}
        title="Patient Portal Invitation"
      >
        <div className="space-y-4 text-center py-4">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-brand-50 text-brand-700">
            <KeyRound size={24} />
          </div>
          <h4 className="text-base font-bold text-ink-900">
            Invitation for {selectedPatient?.full_name}
          </h4>
          <p className="text-xs text-ink-500 max-w-sm mx-auto">
            Provide this secure 8-character invitation code to the patient to activate their HealBytes portal.
          </p>

          <div className="rounded-2xl border-2 border-dashed border-brand-300 bg-brand-50/50 p-6">
            <span className="font-mono text-2xl font-bold tracking-widest text-brand-900">
              {invitationCode || "GENERATING..."}
            </span>
          </div>

          <Button fullWidth onClick={() => setIsInviteOpen(false)}>
            Done
          </Button>
        </div>
      </Modal>
    </div>
  );
}
