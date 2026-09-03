import React from "react";
import { Outlet } from "react-router-dom";
import DoctorSidebar from "./DoctorSidebar";

export default function DoctorLayout() {
  return (
    <div className="flex min-h-screen bg-canvas">
      <DoctorSidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Outlet />
      </div>
    </div>
  );
}
