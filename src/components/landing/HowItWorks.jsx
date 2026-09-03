import React from "react";
import { UserPlus, CalendarCheck, BrainCircuit, BellRing, Stethoscope } from "lucide-react";

export default function HowItWorks() {
  const steps = [
    {
      title: "Patient Onboarding",
      description: "Doctor adds patient and generates a secure invitation.",
      icon: UserPlus,
    },
    {
      title: "Daily Check-ins",
      description: "Patient reports symptoms, wellbeing, and medication adherence.",
      icon: CalendarCheck,
    },
    {
      title: "Intelligent Risk Analysis",
      description: "Check-in information is evaluated to identify potential risk.",
      icon: BrainCircuit,
    },
    {
      title: "Care Team Alerts",
      description: "Important changes are surfaced to the doctor or caretaker.",
      icon: BellRing,
    },
    {
      title: "Coordinated Follow-up",
      description: "Doctors can review the patient, manage medication and schedule follow-up care.",
      icon: Stethoscope,
    },
  ];

  return (
    <section id="how-it-works" className="bg-surface-muted py-24 sm:py-32">
      <div className="mx-auto max-w-7xl px-6 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-bold tracking-tight text-ink-900 sm:text-4xl">
            From discharge to continuous care.
          </h2>
          <p className="mt-4 text-lg text-ink-500">
            A seamless workflow connecting patients and care teams everyday.
          </p>
        </div>
        
        <div className="mx-auto mt-16 max-w-4xl">
          <div className="relative">
            {/* Vertical line connecting steps */}
            <div className="absolute left-8 top-8 bottom-8 w-px bg-ink-300/20 md:left-1/2 md:-ml-px"></div>
            
            <div className="space-y-12">
              {steps.map((step, index) => {
                const Icon = step.icon;
                const isEven = index % 2 === 0;
                
                return (
                  <div key={step.title} className="relative flex items-center md:justify-between flex-col md:flex-row gap-6 md:gap-0">
                    {/* Left side (content or empty) */}
                    <div className={`md:w-5/12 ${isEven ? 'md:text-right md:pr-8' : 'md:order-3 md:pl-8'}`}>
                      <h3 className="text-xl font-bold text-ink-900">{step.title}</h3>
                      <p className="mt-2 text-sm text-ink-600 leading-relaxed">{step.description}</p>
                    </div>
                    
                    {/* Center node */}
                    <div className="absolute left-0 md:static md:w-2/12 flex justify-center md:order-2 z-10">
                      <div className="flex h-16 w-16 items-center justify-center rounded-full border-4 border-surface-muted bg-brand-600 text-white shadow-sm">
                        <Icon size={24} />
                      </div>
                    </div>
                    
                    {/* Right side (empty or content for mobile alignment) */}
                    <div className={`w-full pl-20 md:pl-0 md:w-5/12 ${isEven ? 'md:order-3' : 'hidden md:block md:order-1'}`}>
                      {/* Empty spacer for desktop layout balance */}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
