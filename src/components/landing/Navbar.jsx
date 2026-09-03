import React, { useState } from "react";
import { HeartPulse, Menu, X } from "lucide-react";
import Button from "../ui/Button";

export default function Navbar() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const links = [
    { label: "How It Works", href: "#how-it-works" },
    { label: "Features", href: "#features" },
    { label: "For Patients", href: "#patient-experience" },
    { label: "For Doctors", href: "#doctor-experience" },
    { label: "About", href: "#about" },
  ];

  return (
    <header className="sticky top-0 z-50 w-full border-b border-ink-300/10 bg-canvas/80 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6 lg:px-8">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-700 text-white">
            <HeartPulse size={18} />
          </div>
          <span className="text-xl font-bold text-ink-900">HealBytes</span>
        </div>

        <nav className="hidden md:flex items-center gap-8">
          {links.map((link) => (
            <a
              key={link.label}
              href={link.href}
              className="text-sm font-medium text-ink-500 transition hover:text-ink-900"
            >
              {link.label}
            </a>
          ))}
        </nav>

        <div className="hidden md:flex items-center gap-4">
          <a href="#role-selector">
            <Button>Get Started</Button>
          </a>
        </div>

        <button
          className="md:hidden p-2 text-ink-500 hover:text-ink-900"
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          aria-label="Toggle menu"
        >
          {mobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
        </button>
      </div>

      {mobileMenuOpen && (
        <div className="md:hidden border-t border-ink-300/10 bg-canvas px-6 py-4">
          <div className="flex flex-col gap-4">
            {links.map((link) => (
              <a
                key={link.label}
                href={link.href}
                onClick={() => setMobileMenuOpen(false)}
                className="text-sm font-medium text-ink-700"
              >
                {link.label}
              </a>
            ))}
            <a href="#role-selector" onClick={() => setMobileMenuOpen(false)}>
              <Button fullWidth>Get Started</Button>
            </a>
          </div>
        </div>
      )}
    </header>
  );
}
