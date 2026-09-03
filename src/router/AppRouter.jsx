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
import DoctorAnalytics from "../pages/doctor/Analytics";
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

import { useAuth } from "../context/AuthContext";

function RequireRole({ role, children }) {
  const { role: currentRole, isAuthenticated, ready } = useAuth();
  if (!ready) return null;
  if (!isAuthenticated || currentRole !== role) {
    return <Navigate to={role === "DOCTOR" ? "/doctor/login" : "/patient/login"} replace />;
  }
  return children;
}

export default function AppRouter() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />

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
        <Route path="analytics" element={<DoctorAnalytics />} />
        <Route path="qr-scanner" element={<QRScanner />} />
        <Route path="profile" element={<DoctorProfile />} />
      </Route>

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
        <Route path="alerts" element={<PatientAlerts />} />
        <Route path="analytics" element={<PatientAnalytics />} />
        <Route path="history" element={<PatientHistory />} />
        <Route path="qr" element={<PatientQR />} />
        <Route path="profile" element={<PatientProfilePage />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
