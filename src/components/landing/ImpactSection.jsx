import React from "react";

export default function ImpactSection() {
  const impacts = [
    {
      target: "For Patients",
      description: "Less uncertainty after discharge.",
    },
    {
      target: "For Doctors",
      description: "A clearer view of patients who may need attention.",
    },
    {
      target: "For Care Teams",
      description: "Better coordination between check-ins, alerts and follow-up.",
    },
  ];

  return (
    <section className="bg-canvas py-24 sm:py-32 border-t border-ink-300/10">
      <div className="mx-auto max-w-7xl px-6 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-bold tracking-tight text-ink-900 sm:text-4xl">
            Turning follow-up into continuous care.
          </h2>
        </div>
        
        <div className="mx-auto mt-16 grid max-w-2xl grid-cols-1 gap-8 sm:mt-20 lg:mx-0 lg:max-w-none lg:grid-cols-3">
          {impacts.map((impact) => (
            <div key={impact.target} className="flex flex-col items-center justify-center text-center p-8 bg-surface-muted rounded-3xl">
              <h3 className="text-xl font-bold text-ink-900">{impact.target}</h3>
              <p className="mt-4 text-base text-ink-600">{impact.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
