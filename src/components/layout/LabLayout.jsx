import React from "react";
import { Outlet, NavLink, useNavigate } from "react-router-dom";
import { FlaskConical, ClipboardList, LogOut } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import Button from "../ui/Button";

export default function LabLayout() {
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
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-purple-700 text-white shadow-sm shadow-purple-700/20">
                <FlaskConical size={18} />
              </div>
              <div>
                <p className="text-sm font-bold text-ink-900 leading-tight">HealBytes</p>
                <span className="inline-flex items-center text-[10px] font-semibold text-purple-700 bg-purple-50 px-1.5 py-0.2 rounded">
                  Clinical Diagnostics Laboratory
                </span>
              </div>
            </div>

            <nav className="hidden sm:flex items-center gap-2">
              <NavLink
                to="/lab/dashboard"
                className={({ isActive }) =>
                  `flex items-center gap-2 rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                    isActive ? "bg-purple-50 text-purple-800" : "text-ink-600 hover:bg-canvas-soft"
                  }`
                }
              >
                <ClipboardList size={15} />
                Laboratory Test Queue & Results
              </NavLink>
            </nav>
          </div>

          <div className="flex items-center gap-3">
            <div className="text-right hidden sm:block">
              <p className="text-xs font-semibold text-ink-900">{user?.first_name || user?.username || "Lab Technician"}</p>
              <p className="text-[10px] text-ink-400">Medical Laboratory Scientist</p>
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
