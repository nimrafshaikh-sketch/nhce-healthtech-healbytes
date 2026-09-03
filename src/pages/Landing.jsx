import React from "react";
import Navbar from "../components/landing/Navbar";
import Hero from "../components/landing/Hero";
import RoleSelector from "../components/landing/RoleSelector";
import HowItWorks from "../components/landing/HowItWorks";
import Features from "../components/landing/Features";
import PatientSection from "../components/landing/PatientSection";
import DoctorSection from "../components/landing/DoctorSection";
import AISection from "../components/landing/AISection";
import TrustSection from "../components/landing/TrustSection";
import ImpactSection from "../components/landing/ImpactSection";
import AboutSection from "../components/landing/AboutSection";
import CTASection from "../components/landing/CTASection";
import Footer from "../components/landing/Footer";

export default function Landing() {
  return (
    <div className="min-h-screen bg-canvas font-sans selection:bg-brand-200 selection:text-brand-900">
      <Navbar />
      <main>
        <Hero />
        <RoleSelector />
        <HowItWorks />
        <Features />
        <PatientSection />
        <DoctorSection />
        <AISection />
        <TrustSection />
        <ImpactSection />
        <AboutSection />
        <CTASection />
      </main>
      <Footer />
    </div>
  );
}
