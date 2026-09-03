import React from "react";
import { NavLink } from "react-router-dom";
import { Home, ClipboardCheck, Pill, LineChart, UserCircle } from "lucide-react";

const NAV = [
  { to: "/patient/home", label: "Home", icon: Home },
  { to: "/patient/check-in", label: "Check-in", icon: ClipboardCheck },
  { to: "/patient/medicines", label: "Medicines", icon: Pill },
  { to: "/patient/analytics", label: "Insights", icon: LineChart },
  { to: "/patient/profile", label: "Profile", icon: UserCircle },
];

export default function PatientBottomNav() {
  return (
    <nav className="safe-bottom fixed inset-x-0 bottom-0 z-40 border-t border-ink-300/15 bg-white/95 backdrop-blur">
      <div className="mx-auto flex max-w-md items-stretch justify-between px-1">
        {NAV.map(({ to, label, icon: Icon }) => (
          <NavLink key={to} to={to} className="flex flex-1 flex-col items-center gap-1 py-2.5 text-[11px] font-medium">
            {({ isActive }) => (
              <>
                <Icon size={20} strokeWidth={isActive ? 2.4 : 2} className={isActive ? "text-brand-700" : "text-ink-300"} />
                <span className={isActive ? "text-brand-700" : "text-ink-300"}>{label}</span>
              </>
            )}
          </NavLink>
        ))}
      </div>
    </nav>
  );
}
