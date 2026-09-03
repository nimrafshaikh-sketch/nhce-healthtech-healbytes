import React from "react";
import { useNavigate } from "react-router-dom";
import { LogOut } from "lucide-react";
import Avatar from "../../components/ui/Avatar";
import Button from "../../components/ui/Button";
import { useAuth } from "../../context/AuthContext";
import { useData } from "../../context/DataContext";

export default function PatientProfilePage() {
  const { user, logout } = useAuth();
  const { getPatientById } = useData();
  const navigate = useNavigate();
  const patient = getPatientById(user.id) || user;

  function handleLogout() {
    logout();
    navigate("/patient/login");
  }

  return (
    <div className="flex-1 px-5 pb-6 pt-8">
      <h1 className="text-lg font-semibold text-ink-900">Profile</h1>

      <div className="mt-5 flex items-center gap-4 rounded-2xl border border-ink-300/15 bg-white p-5 shadow-card">
        <Avatar name={patient.name} initials={patient.avatarInitials} size="lg" />
        <div>
          <p className="text-base font-semibold text-ink-900">{patient.name}</p>
          <p className="text-sm text-ink-500">{patient.condition}</p>
          <p className="text-xs text-ink-300">{patient.email}</p>
        </div>
      </div>

      <div className="mt-4 rounded-2xl border border-ink-300/15 bg-white p-5 shadow-card">
        <p className="text-xs font-semibold uppercase tracking-wide text-ink-300">Caretaker</p>
        <p className="mt-1 text-sm text-ink-800">
          {patient.caretaker?.name} · {patient.caretaker?.relationship}
        </p>
        <p className="text-sm text-ink-500">{patient.caretaker?.phone}</p>
      </div>

      <Button variant="secondary" fullWidth className="mt-6" leftIcon={<LogOut size={15} />} onClick={handleLogout}>
        Sign Out
      </Button>
    </div>
  );
}
