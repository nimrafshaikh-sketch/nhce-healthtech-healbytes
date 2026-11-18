import React, { Suspense, lazy } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const Landing = lazy(() => import("../pages/Landing"));

const DoctorLayout = lazy(() => import("../components/layout/DoctorLayout"));
const DoctorLogin = lazy(() => import("../pages/doctor/Login"));
const DoctorDashboard = lazy(() => import("../pages/doctor/Dashboard"));
const Patients = lazy(() => import("../pages/doctor/Patients"));
const AddPatient = lazy(() => import("../pages/doctor/AddPatient"));
const DoctorPatientProfile = lazy(() => import("../pages/doctor/PatientProfile"));
const DoctorAlerts = lazy(() => import("../pages/doctor/Alerts"));
const QRScanner = lazy(() => import("../pages/doctor/QRScanner"));
const DoctorProfile = lazy(() => import("../pages/doctor/Profile"));

const PatientLayout = lazy(() => import("../components/layout/PatientLayout"));
const PatientLogin = lazy(() => import("../pages/patient/Login"));
const InvitationOnboarding = lazy(() => import("../pages/patient/InvitationOnboarding"));
const PatientHome = lazy(() => import("../pages/patient/Home"));
const PatientAppointments = lazy(() => import("../pages/patient/Appointments"));
const CheckIn = lazy(() => import("../pages/patient/CheckIn"));
const Medicines = lazy(() => import("../pages/patient/Medicines"));
const PatientAlerts = lazy(() => import("../pages/patient/Alerts"));
const PatientAnalytics = lazy(() => import("../pages/patient/Analytics"));
const PatientHistory = lazy(() => import("../pages/patient/History"));
const PatientQR = lazy(() => import("../pages/patient/QR"));
const PatientProfilePage = lazy(() => import("../pages/patient/Profile"));
const PatientLabResults = lazy(() => import("../pages/patient/LabResults"));

const ReceptionistLayout = lazy(() => import("../components/layout/ReceptionistLayout"));
const ReceptionistLogin = lazy(() => import("../pages/receptionist/Login"));
const ReceptionistDashboard = lazy(() => import("../pages/receptionist/Dashboard"));
const ReceptionistNewPatient = lazy(() => import("../pages/receptionist/NewPatient"));

const LabLayout = lazy(() => import("../components/layout/LabLayout"));
const LabLogin = lazy(() => import("../pages/lab/Login"));
const LabDashboard = lazy(() => import("../pages/lab/Dashboard"));

function roleHomePath(role) {
  const normalized = role ? String(role).toUpperCase() : null;
  if (normalized === "DOCTOR") return "/doctor/dashboard";
  if (normalized === "RECEPTIONIST") return "/receptionist/dashboard";
  if (normalized === "LAB_TECH") return "/lab/dashboard";
  if (normalized === "PATIENT") return "/patient/home";
  return "/";
}

function AuthInitializingScreen() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-canvas px-6">
      <div className="flex flex-col items-center gap-3 text-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-600 border-t-transparent" />
        <p className="text-sm font-medium text-ink-600">Restoring your session…</p>
      </div>
    </div>
  );
}

function RequireRole({ role, children }) {
  const { role: currentRole, isAuthenticated, ready } = useAuth();
  if (!ready) return <AuthInitializingScreen />;
  const cur = currentRole ? String(currentRole).toUpperCase() : null;
  const exp = role ? String(role).toUpperCase() : null;
  if (!isAuthenticated || cur !== exp) {
    if (exp === "DOCTOR") return <Navigate to="/doctor/login" replace />;
    if (exp === "RECEPTIONIST") return <Navigate to="/receptionist/login" replace />;
    if (exp === "LAB_TECH") return <Navigate to="/lab/login" replace />;
    return <Navigate to="/patient/login" replace />;
  }
  return children;
}

function GuestOnlyRoute({ role, children }) {
  const { role: currentRole, isAuthenticated, ready } = useAuth();
  if (!ready) return <AuthInitializingScreen />;
  const cur = currentRole ? String(currentRole).toUpperCase() : null;
  const exp = role ? String(role).toUpperCase() : null;
  if (isAuthenticated && cur === exp) {
    return <Navigate to={roleHomePath(cur)} replace />;
  }
  return children;
}

function RouteLoadingScreen() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-canvas px-6">
      <div className="flex flex-col items-center gap-3 text-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-600 border-t-transparent" />
        <p className="text-sm font-medium text-ink-600">Loading…</p>
      </div>
    </div>
  );
}

export default function AppRouter() {
  return (
    <Suspense fallback={<RouteLoadingScreen />}>
      <Routes>
      <Route path="/" element={<Landing />} />

      {/* Doctor Portal */}
      <Route
        path="/doctor/login"
        element={
          <GuestOnlyRoute role="DOCTOR">
            <DoctorLogin />
          </GuestOnlyRoute>
        }
      />
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
      <Route
        path="/patient/login"
        element={
          <GuestOnlyRoute role="PATIENT">
            <PatientLogin />
          </GuestOnlyRoute>
        }
      />
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
        <Route path="appointments" element={<PatientAppointments />} />
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
      <Route
        path="/receptionist/login"
        element={
          <GuestOnlyRoute role="RECEPTIONIST">
            <ReceptionistLogin />
          </GuestOnlyRoute>
        }
      />
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
      <Route
        path="/lab/login"
        element={
          <GuestOnlyRoute role="LAB_TECH">
            <LabLogin />
          </GuestOnlyRoute>
        }
      />
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
    </Suspense>
  );
}
