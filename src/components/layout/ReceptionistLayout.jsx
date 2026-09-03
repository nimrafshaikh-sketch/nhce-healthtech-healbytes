import React from "react";
import { Outlet, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { Users, LogOut, Activity } from "lucide-react";

export default function ReceptionistLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = () => {
    logout();
    navigate("/");
  };

  const navItems = [
    { name: "Dashboard", path: "/receptionist/dashboard", icon: Users },
  ];

  return (
    <div className="flex h-screen bg-canvas">
      {/* Sidebar */}
      <aside className="w-64 border-r border-ink-300/20 bg-white flex flex-col">
        <div className="flex h-16 items-center px-6 border-b border-ink-300/20">
          <Activity className="text-brand-600 mr-2" size={24} />
          <span className="font-semibold text-lg text-ink-900">HealBytes Desk</span>
        </div>
        
        <div className="p-4 flex-1">
          <div className="mb-6 px-3">
            <p className="text-sm font-medium text-ink-900">{user?.name}</p>
            <p className="text-xs text-ink-500">Receptionist</p>
          </div>
          
          <nav className="space-y-1">
            {navItems.map((item) => {
              const isActive = location.pathname.startsWith(item.path);
              const Icon = item.icon;
              return (
                <button
                  key={item.name}
                  onClick={() => navigate(item.path)}
                  className={`w-full flex items-center px-3 py-2 text-sm font-medium rounded-lg transition-colors ${
                    isActive
                      ? "bg-brand-50 text-brand-700"
                      : "text-ink-600 hover:bg-ink-100 hover:text-ink-900"
                  }`}
                >
                  <Icon className="mr-3" size={18} />
                  {item.name}
                </button>
              );
            })}
          </nav>
        </div>
        
        <div className="p-4 border-t border-ink-300/20">
          <button
            onClick={handleLogout}
            className="w-full flex items-center px-3 py-2 text-sm font-medium text-red-600 rounded-lg hover:bg-red-50 transition-colors"
          >
            <LogOut className="mr-3" size={18} />
            Sign Out
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto bg-canvas">
        <Outlet />
      </main>
    </div>
  );
}
