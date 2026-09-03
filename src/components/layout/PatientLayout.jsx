import React from "react";
import { Outlet } from "react-router-dom";
import PatientBottomNav from "./PatientBottomNav";

export default function PatientLayout() {
  return (
    <div className="mx-auto flex min-h-screen max-w-md flex-col bg-canvas pb-24">
      <Outlet />
      <PatientBottomNav />
    </div>
  );
}
