import React from "react";
import { Activity, CalendarCheck, Pill, Bell, Stethoscope, Lock } from "lucide-react";

export default function Features() {
  const features = [
    {
      name: "Intelligent Risk Monitoring",
      description: "Identify concerning changes in patient-reported symptoms and wellbeing.",
      icon: Activity,
    },
    {
      name: "Daily Patient Check-ins",
      description: "Simple mobile-first check-ins help patients communicate how they are doing.",
      icon: CalendarCheck,
    },
    {
      name: "Medication Follow-up",
      description: "Patients can view medications and track whether doses were taken.",
      icon: Pill,
    },
    {
      name: "Doctor Alerts",
      description: "Important risk signals are surfaced to the care team for review.",
      icon: Bell,
    },
    {
      name: "Follow-up Coordination",
      description: "Doctors can review patient status and coordinate follow-up care.",
      icon: Stethoscope,
    },
    {
      name: "Secure Patient Access",
      description: "Invitation-based onboarding and protected patient information help keep access controlled.",
      icon: Lock,
    },
  ];

  return (
    <section id="features" className="bg-canvas py-24 sm:py-32">
      <div className="mx-auto max-w-7xl px-6 lg:px-8">
        <div className="mx-auto max-w-2xl lg:text-center">
          <h2 className="text-base font-semibold leading-7 text-brand-600 uppercase tracking-wider">Features</h2>
          <p className="mt-2 text-3xl font-bold tracking-tight text-ink-900 sm:text-4xl">
            Everything you need for continuous care
          </p>
          <p className="mt-6 text-lg leading-8 text-ink-500">
            HealBytes provides a structured, intelligent connection between the care team and the patient.
          </p>
        </div>
        <div className="mx-auto mt-16 max-w-2xl sm:mt-20 lg:mt-24 lg:max-w-none">
          <dl className="grid max-w-xl grid-cols-1 gap-x-8 gap-y-16 lg:max-w-none lg:grid-cols-3">
            {features.map((feature) => (
              <div key={feature.name} className="flex flex-col">
                <dt className="flex items-center gap-x-3 text-base font-semibold leading-7 text-ink-900">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
                    <feature.icon className="h-5 w-5" aria-hidden="true" />
                  </div>
                  {feature.name}
                </dt>
                <dd className="mt-4 flex flex-auto flex-col text-base leading-7 text-ink-600">
                  <p className="flex-auto">{feature.description}</p>
                </dd>
              </div>
            ))}
          </dl>
        </div>
      </div>
    </section>
  );
}
