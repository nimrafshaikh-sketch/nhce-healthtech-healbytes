import React from "react";
import { NavLink } from "react-router-dom";
import { LayoutGrid, Users, Bell, BarChart3, QrCode, UserCircle, Stethoscope } from "lucide-react";
import { useData } from "../../context/DataContext";

const NAV = [
  { to: "/doctor/dashboard", label: "Overview", icon: LayoutGrid },
  { to: "/doctor/patients", label: "Patients", icon: Users },
  { to: "/doctor/alerts", label: "Alerts", icon: Bell, badge: true },
  { to: "/doctor/analytics", label: "Analytics", icon: BarChart3 },
];

function linkClass({ isActive }) {
  return `flex items-center justify-between rounded-xl px-3 py-2.5 text-sm font-medium transition ${
    isActive ? "bg-brand-50 text-brand-800" : "text-ink-600 hover:bg-canvas-soft"
  }`;
}

export default function DoctorSidebar() {
  const { activeAlertCount } = useData();
  return (
    <aside className="hidden w-64 shrink-0 flex-col border-r border-ink-300/15 bg-white px-4 py-6 lg:flex">
      <div className="mb-8 flex items-center gap-2 px-2">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-700 text-white">
          <Stethoscope size={18} />
        </div>
        <div>
          <p className="text-sm font-bold leading-tight text-ink-900">HealBytes</p>
          <p className="text-[11px] leading-tight text-ink-300">Doctor</p>
        </div>
      </div>

      <nav className="flex flex-1 flex-col gap-1">
        {NAV.map(({ to, label, icon: Icon, badge }) => (
          <NavLink key={to} to={to} className={linkClass}>
            <span className="flex items-center gap-2.5">
              <Icon size={17} />
              {label}
            </span>
            {badge && activeAlertCount > 0 && (
              <span className="rounded-full bg-risk-high px-1.5 py-0.5 text-[10px] font-semibold text-white">
                {activeAlertCount}
              </span>
            )}
          </NavLink>
        ))}

        <div className="my-3 h-px bg-ink-300/15" />

        <NavLink to="/doctor/qr-scanner" className={linkClass}>
          <span className="flex items-center gap-2.5">
            <QrCode size={17} /> QR Scanner
          </span>
        </NavLink>

        <div className="my-3 h-px bg-ink-300/15" />

        <NavLink to="/doctor/profile" className={linkClass}>
          <span className="flex items-center gap-2.5">
            <UserCircle size={17} /> Profile
          </span>
        </NavLink>
      </nav>
    </aside>
  );
}
