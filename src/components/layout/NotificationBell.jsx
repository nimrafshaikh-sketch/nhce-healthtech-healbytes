import React, { useEffect, useRef, useState } from "react";
import { Bell } from "lucide-react";
import { getNotifications, getUnreadNotificationCount, markNotificationRead } from "../../api/notifications.api";
import { formatRelativeTime } from "../../utils/dateUtils";

// Generic in-app Notification bell (appointments, lab results, medication
// reminders, invitations, etc - apps.notifications.Notification). Previously
// this was only ever wired up for the LAB_TECH role (components/layout/
// LabLayout.jsx) - Doctor, Patient, and Receptionist had no notification UI
// at all, even though the backend has been creating these rows the whole
// time (see backend/apps/*/tasks.py). This is deliberately a separate
// concept from the doctor's AI-generated risk "Alerts" (DataContext.alerts,
// pages/doctor/Alerts.jsx / pages/patient/Alerts.jsx) - both stay.
export default function NotificationBell({ className = "" }) {
  const [open, setOpen] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const containerRef = useRef(null);

  useEffect(() => {
    let active = true;
    function poll() {
      getUnreadNotificationCount()
        .then((count) => active && setUnreadCount(count))
        .catch(() => {});
    }
    poll();
    const interval = setInterval(poll, 20000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, []);

  useEffect(() => {
    function handleClickOutside(e) {
      if (containerRef.current && !containerRef.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  function toggleOpen() {
    const next = !open;
    setOpen(next);
    if (next) {
      setLoading(true);
      setError(null);
      getNotifications()
        .then((list) => setNotifications(list.slice(0, 10)))
        .catch((err) => setError(err.message || "Could not load notifications."))
        .finally(() => setLoading(false));
    }
  }

  async function handleItemClick(n) {
    if (!n.is_read) {
      try {
        await markNotificationRead(n.id);
        setNotifications((list) => list.map((x) => (x.id === n.id ? { ...x, is_read: true } : x)));
        setUnreadCount((c) => Math.max(0, c - 1));
      } catch {
        // leave as-is, not critical
      }
    }
  }

  return (
    <div ref={containerRef} className={`relative ${className}`}>
      <button
        onClick={toggleOpen}
        aria-label="Notifications"
        className="relative rounded-full p-2 text-ink-600 hover:bg-white"
      >
        <Bell size={18} />
        {unreadCount > 0 && (
          <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-risk-high px-1 text-[10px] font-semibold text-white">
            {unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 z-40 mt-2 w-80 max-w-[90vw] rounded-2xl border border-ink-300/15 bg-white p-2 shadow-raised">
          <p className="px-2.5 py-1.5 text-xs font-semibold uppercase tracking-wide text-ink-300">Notifications</p>
          {loading ? (
            <p className="px-2.5 py-4 text-center text-sm text-ink-500">Loading…</p>
          ) : error ? (
            <p className="px-2.5 py-4 text-center text-sm text-risk-high">{error}</p>
          ) : notifications.length === 0 ? (
            <p className="px-2.5 py-4 text-center text-sm text-ink-500">You're all caught up.</p>
          ) : (
            <div className="max-h-80 space-y-0.5 overflow-y-auto">
              {notifications.map((n) => (
                <button
                  key={n.id}
                  onClick={() => handleItemClick(n)}
                  className={`block w-full rounded-xl px-2.5 py-2 text-left text-sm transition hover:bg-canvas-soft ${
                    n.is_read ? "text-ink-500" : "text-ink-900"
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <span className={`font-medium ${n.is_read ? "" : "font-semibold"}`}>{n.title}</span>
                    {!n.is_read && <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-brand-600" />}
                  </div>
                  {n.body && <p className="mt-0.5 text-xs text-ink-500">{n.body}</p>}
                  <p className="mt-1 text-[11px] text-ink-300">{formatRelativeTime(n.created_at)}</p>
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
