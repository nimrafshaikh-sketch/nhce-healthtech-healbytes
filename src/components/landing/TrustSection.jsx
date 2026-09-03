import React from "react";
import { Shield, Key, Users, QrCode } from "lucide-react";

export default function TrustSection() {
  const features = [
    {
      name: "Role-based access",
      description: "Separate portals and permissions for patients and doctors.",
      icon: Users,
    },
    {
      name: "Invitation-based onboarding",
      description: "Patients only join via a direct invitation from their care team.",
      icon: Key,
    },
    {
      name: "Protected patient access",
      description: "Patient information is secure and accessible only to authorized members.",
      icon: Shield,
    },
    {
      name: "Controlled QR access",
      description: "Optional QR-based quick access for secure clinical environments.",
      icon: QrCode,
    },
  ];

  return (
    <section className="bg-surface py-24 sm:py-32">
      <div className="mx-auto max-w-7xl px-6 lg:px-8">
        <div className="mx-auto max-w-2xl lg:text-center">
          <h2 className="text-base font-semibold leading-7 text-brand-600 uppercase tracking-wider">Trust &amp; Security</h2>
          <p className="mt-2 text-3xl font-bold tracking-tight text-ink-900 sm:text-4xl">
            Built for coordinated care.
          </p>
          <p className="mt-6 text-lg leading-8 text-ink-500">
            HealBytes is designed with the safety, privacy, and coordination of healthcare teams and their patients in mind.
          </p>
        </div>
        
        <div className="mx-auto mt-16 max-w-2xl sm:mt-20 lg:mt-24 lg:max-w-none">
          <dl className="grid max-w-xl grid-cols-1 gap-x-8 gap-y-10 lg:max-w-none lg:grid-cols-4">
            {features.map((feature) => (
              <div key={feature.name} className="flex flex-col border border-ink-300/20 rounded-2xl p-6 bg-white shadow-sm">
                <dt className="flex items-center gap-x-3 text-sm font-semibold leading-7 text-ink-900">
                  <feature.icon className="h-5 w-5 text-brand-600" aria-hidden="true" />
                  {feature.name}
                </dt>
                <dd className="mt-4 flex flex-auto flex-col text-sm leading-6 text-ink-600">
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
