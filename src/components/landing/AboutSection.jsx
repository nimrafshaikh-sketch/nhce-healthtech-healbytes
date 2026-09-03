import React from "react";

export default function AboutSection() {
  return (
    <section id="about" className="bg-surface py-24 sm:py-32">
      <div className="mx-auto max-w-7xl px-6 lg:px-8">
        <div className="mx-auto max-w-3xl text-center">
          <h2 className="text-base font-semibold leading-7 text-brand-600 uppercase tracking-wider">About</h2>
          <p className="mt-2 text-3xl font-bold tracking-tight text-ink-900 sm:text-4xl">
            Bridging the gap between hospital and home.
          </p>
          <p className="mt-6 text-lg leading-8 text-ink-600">
            HealBytes is an AI-assisted healthcare coordination and follow-up platform designed to bridge the gap between hospital discharge and ongoing patient care.
          </p>
          <p className="mt-4 text-lg leading-8 text-ink-600">
            The product connects <span className="font-semibold text-ink-900">Patients</span>, <span className="font-semibold text-ink-900">Doctors</span>, and <span className="font-semibold text-ink-900">Care Teams</span> through check-ins, risk assessment, alerts, medications, and follow-up workflows.
          </p>
        </div>
      </div>
    </section>
  );
}
