import React from "react";
import { Outlet, NavLink, useNavigate } from "react-router-dom";
import { Users, Calendar, LogOut, HeartPulse, Sparkles } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import Button from "../ui/Button";

export default function ReceptionistLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <div className="min-h-screen bg-canvas">
      {/* Top Navigation */}
      <header className="sticky top-0 z-30 border-b border-ink-100 bg-white/95 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2.5">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-700 text-white shadow-sm shadow-brand-700/20">
                <HeartPulse size={18} />
              </div>
              <div>
                <p className="text-sm font-bold text-ink-900 leading-tight">HealBytes</p>
                <span className="inline-flex items-center text-[10px] font-semibold text-brand-700 bg-brand-50 px-1.5 py-0.2 rounded">
                  Reception Desk
                </span>
              </div>
            </div>

            <nav className="hidden sm:flex items-center gap-2">
              <NavLink
                to="/receptionist/dashboard"
                className={({ isActive }) =>
                  `flex items-center gap-2 rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                    isActive ? "bg-brand-50 text-brand-800" : "text-ink-600 hover:bg-canvas-soft"
                  }`
                }
              >
                <Users size={15} />
                Patient Services & Appointments
              </NavLink>
            </nav>
          </div>

          <div className="flex items-center gap-3">
            <div className="text-right hidden sm:block">
              <p className="text-xs font-semibold text-ink-900">{user?.first_name || user?.username || "Reception Staff"}</p>
              <p className="text-[10px] text-ink-400">Front Desk Officer</p>
            </div>
            <Button variant="ghost" size="sm" onClick={handleLogout} className="text-ink-500 hover:text-red-600">
              <LogOut size={16} />
              <span className="hidden sm:inline ml-1.5">Sign Out</span>
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <Outlet />
      </main>
    </div>
  );
}
