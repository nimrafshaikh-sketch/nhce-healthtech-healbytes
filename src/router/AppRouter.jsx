import React from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import Landing from "../pages/Landing";

import DoctorLayout from "../components/layout/DoctorLayout";
import DoctorLogin from "../pages/doctor/Login";
import DoctorDashboard from "../pages/doctor/Dashboard";
import Patients from "../pages/doctor/Patients";
import AddPatient from "../pages/doctor/AddPatient";
import DoctorPatientProfile from "../pages/doctor/PatientProfile";
import DoctorAlerts from "../pages/doctor/Alerts";
// DoctorAnalytics (pages/doctor/Analytics.jsx) intentionally not imported/
// routed here - Part 10: Analytics removed from the Doctor Dashboard. The
// file is left in place (unused) rather than deleted, in case it's wanted
// again; the component and its API call are otherwise fully disconnected.
import QRScanner from "../pages/doctor/QRScanner";
import DoctorProfile from "../pages/doctor/Profile";

import PatientLayout from "../components/layout/PatientLayout";
import PatientLogin from "../pages/patient/Login";
import InvitationOnboarding from "../pages/patient/InvitationOnboarding";
import PatientHome from "../pages/patient/Home";
import CheckIn from "../pages/patient/CheckIn";
import Medicines from "../pages/patient/Medicines";
import PatientAlerts from "../pages/patient/Alerts";
import PatientAnalytics from "../pages/patient/Analytics";
import PatientHistory from "../pages/patient/History";
import PatientQR from "../pages/patient/QR";
import PatientProfilePage from "../pages/patient/Profile";
import PatientLabResults from "../pages/patient/LabResults";

import ReceptionistLayout from "../components/layout/ReceptionistLayout";
import ReceptionistLogin from "../pages/receptionist/Login";
import ReceptionistDashboard from "../pages/receptionist/Dashboard";
import ReceptionistNewPatient from "../pages/receptionist/NewPatient";

import LabLayout from "../components/layout/LabLayout";
import LabLogin from "../pages/lab/Login";
import LabDashboard from "../pages/lab/Dashboard";
// pages/lab/Queue.jsx and pages/lab/TestDetail.jsx intentionally not
// imported/routed here - they were an orphaned duplicate lab-tech flow
// (uppercase mock statuses like "COMPLETED" that never match the real
// backend's lowercase status choices, and fields like req.testType/
// req.patientName that don't exist on the live LabTestRequest response),
// reachable only by typing /lab/queue directly since no nav link in
// LabLayout.jsx points at it anymore. pages/lab/Dashboard.jsx is the one
// real, working implementation (queue + claim + submit results in one
// page, correctly wired to apps.labtests) and now covers this fully.

import { useAuth } from "../context/AuthContext";

function RequireRole({ role, children }) {
  const { role: currentRole, isAuthenticated, ready } = useAuth();
  if (!ready) return null;
  if (!isAuthenticated || currentRole !== role) {
    if (role === "DOCTOR") return <Navigate to="/doctor/login" replace />;
    if (role === "RECEPTIONIST") return <Navigate to="/receptionist/login" replace />;
    if (role === "LAB_TECH") return <Navigate to="/lab/login" replace />;
    return <Navigate to="/patient/login" replace />;
  }
  return children;
}

export default function AppRouter() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />

      {/* Doctor Portal */}
      <Route path="/doctor/login" element={<DoctorLogin />} />
      <Route
        path="/doctor"
        element={
          <RequireRole role="DOCTOR">
            <DoctorLayout />
          </RequireRole>
        }
      >
        <Route index element={<Navigate to="dashboard" replace />} />
        <Route path="dashboard" element={<DoctorDashboard />} />
        <Route path="patients" element={<Patients />} />
        <Route path="patients/new" element={<AddPatient />} />
        <Route path="patients/:id" element={<DoctorPatientProfile />} />
        <Route path="patients/:id/medications" element={<DoctorPatientProfile />} />
        <Route path="alerts" element={<DoctorAlerts />} />
        <Route path="qr-scanner" element={<QRScanner />} />
        <Route path="profile" element={<DoctorProfile />} />
      </Route>

      {/* Patient Portal */}
      <Route path="/patient/login" element={<PatientLogin />} />
      <Route path="/patient/register" element={<InvitationOnboarding />} />
      <Route
        path="/patient"
        element={
          <RequireRole role="PATIENT">
            <PatientLayout />
          </RequireRole>
        }
      >
        <Route index element={<Navigate to="home" replace />} />
        <Route path="home" element={<PatientHome />} />
        <Route path="check-in" element={<CheckIn />} />
        <Route path="medicines" element={<Medicines />} />
        <Route path="labs" element={<PatientLabResults />} />
        <Route path="alerts" element={<PatientAlerts />} />
        <Route path="analytics" element={<PatientAnalytics />} />
        <Route path="history" element={<PatientHistory />} />
        <Route path="qr" element={<PatientQR />} />
        <Route path="profile" element={<PatientProfilePage />} />
      </Route>

      {/* Receptionist Portal */}
      <Route path="/receptionist/login" element={<ReceptionistLogin />} />
      <Route
        path="/receptionist"
        element={
          <RequireRole role="RECEPTIONIST">
            <ReceptionistLayout />
          </RequireRole>
        }
      >
        <Route index element={<Navigate to="dashboard" replace />} />
        <Route path="dashboard" element={<ReceptionistDashboard />} />
        <Route path="patients/new" element={<ReceptionistNewPatient />} />
      </Route>

      {/* Lab Technician Portal */}
      <Route path="/lab/login" element={<LabLogin />} />
      <Route
        path="/lab"
        element={
          <RequireRole role="LAB_TECH">
            <LabLayout />
          </RequireRole>
        }
      >
        <Route index element={<Navigate to="dashboard" replace />} />
        <Route path="dashboard" element={<LabDashboard />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
