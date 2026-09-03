import React from "react";
import { Bell, Search } from "lucide-react";
import Avatar from "../ui/Avatar";
import { useAuth } from "../../context/AuthContext";
import { useData } from "../../context/DataContext";
import { useNavigate } from "react-router-dom";

export default function Topbar({ title, subtitle }) {
  const { user } = useAuth();
  const { activeAlertCount } = useData();
  const navigate = useNavigate();

  return (
    <header className="sticky top-0 z-30 flex items-center justify-between gap-4 border-b border-ink-300/15 bg-canvas/90 px-6 py-4 backdrop-blur">
      <div className="min-w-0">
        <h1 className="truncate text-lg font-semibold text-ink-900">{title}</h1>
        {subtitle && <p className="truncate text-sm text-ink-500">{subtitle}</p>}
      </div>
      <div className="flex shrink-0 items-center gap-3">
        <div className="hidden items-center gap-2 rounded-xl border border-ink-300/25 bg-white px-3 py-2 text-sm text-ink-400 md:flex">
          <Search size={15} />
          <span>Search patients…</span>
        </div>
        <button
          onClick={() => navigate("/doctor/alerts")}
          aria-label="Alerts"
          className="relative rounded-full p-2 text-ink-600 hover:bg-white"
        >
          <Bell size={18} />
          {activeAlertCount > 0 && (
            <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-risk-high px-1 text-[10px] font-semibold text-white">
              {activeAlertCount}
            </span>
          )}
        </button>
        <Avatar name={user?.name} initials={user?.avatarInitials} />
      </div>
    </header>
  );
}
