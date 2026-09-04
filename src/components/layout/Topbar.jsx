import React from "react";
import { Search } from "lucide-react";
import Avatar from "../ui/Avatar";
import NotificationBell from "./NotificationBell";
import { useAuth } from "../../context/AuthContext";
import { useNavigate } from "react-router-dom";

// The search box below is intentionally decorative-only (no working patient
// search here) - the doctor's real, working patient search lives on
// pages/doctor/Patients.jsx (see api/patients.api.js::searchMyPatients).
// The bell used to just be a shortcut to /doctor/alerts (already reachable
// via the sidebar's own "Alerts" nav item, badge and all - see
// DoctorSidebar.jsx) - it's now the real in-app Notifications bell instead
// (appointments, lab results, medication reminders, etc), which had no UI
// anywhere for the Doctor role before.
export default function Topbar({ title, subtitle }) {
  const { user } = useAuth();
  const navigate = useNavigate();

  return (
    <header className="sticky top-0 z-30 flex items-center justify-between gap-4 border-b border-ink-300/15 bg-canvas/90 px-6 py-4 backdrop-blur">
      <div className="min-w-0">
        <h1 className="truncate text-lg font-semibold text-ink-900">{title}</h1>
        {subtitle && <p className="truncate text-sm text-ink-500">{subtitle}</p>}
      </div>
      <div className="flex shrink-0 items-center gap-3">
        <button
          onClick={() => navigate("/doctor/patients")}
          className="hidden items-center gap-2 rounded-xl border border-ink-300/25 bg-white px-3 py-2 text-sm text-ink-400 hover:border-brand-200 md:flex"
        >
          <Search size={15} />
          <span>Search patients…</span>
        </button>
        <NotificationBell />
        <Avatar name={user?.name} initials={user?.avatarInitials} />
      </div>
    </header>
  );
}
