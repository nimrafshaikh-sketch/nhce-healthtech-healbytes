import React from "react";
import { useNavigate } from "react-router-dom";
import { LogOut } from "lucide-react";
import Topbar from "../../components/layout/Topbar";
import Avatar from "../../components/ui/Avatar";
import Button from "../../components/ui/Button";
import { useAuth } from "../../context/AuthContext";

export default function DoctorProfile() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/doctor/login");
  }

  return (
    <>
      <Topbar title="Profile" subtitle="Your account details." />
      <main className="flex-1 px-6 py-6">
        <div className="mx-auto max-w-md rounded-2xl border border-ink-300/15 bg-white p-6 shadow-card">
          <div className="flex items-center gap-4">
            <Avatar name={user?.name} initials={user?.avatarInitials} size="lg" />
            <div>
              <p className="text-base font-semibold text-ink-900">{user?.name}</p>
              <p className="text-sm text-ink-500">{user?.specialty}</p>
              <p className="text-xs text-ink-300">{user?.email}</p>
            </div>
          </div>
          <Button variant="secondary" fullWidth className="mt-6" leftIcon={<LogOut size={15} />} onClick={handleLogout}>
            Sign Out
          </Button>
        </div>
      </main>
    </>
  );
}
