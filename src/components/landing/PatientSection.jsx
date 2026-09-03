import React from "react";
import { CheckCircle2, ShieldCheck, Pill } from "lucide-react";

export default function PatientSection() {
  return (
    <section id="patient-experience" className="overflow-hidden bg-surface-muted py-24 sm:py-32">
      <div className="mx-auto max-w-7xl px-6 lg:px-8">
        <div className="mx-auto grid max-w-2xl grid-cols-1 gap-x-16 gap-y-16 sm:gap-y-20 lg:mx-0 lg:max-w-none lg:grid-cols-2 lg:items-center">
          
          <div className="relative order-2 lg:order-1">
            {/* Abstract UI representation of Patient App */}
            <div className="mx-auto w-[300px] sm:w-[340px] rounded-[2.5rem] border-8 border-ink-900 bg-canvas p-4 shadow-2xl relative overflow-hidden h-[600px] flex flex-col">
              {/* Fake Mobile Status Bar */}
              <div className="h-6 w-full mb-4 flex justify-between items-center px-2">
                <span className="text-[10px] font-medium text-ink-900">9:41</span>
                <div className="flex gap-1 h-3 items-center">
                  <div className="w-4 h-2.5 bg-ink-900 rounded-sm"></div>
                </div>
              </div>
              
              <div className="flex-1 overflow-hidden flex flex-col gap-4">
                <div className="px-2">
                  <p className="text-xs text-ink-500">Good morning,</p>
                  <h3 className="text-xl font-bold text-ink-900">Sarah</h3>
                </div>

                {/* Checkin CTA Mock */}
                <div className="bg-brand-700 text-white p-5 rounded-2xl shadow-card mx-2">
                  <div className="flex justify-between items-start mb-4">
                    <div className="bg-brand-600 p-2 rounded-xl">
                      <ShieldCheck size={20} />
                    </div>
                  </div>
                  <h4 className="font-bold mb-1">Today's Check-in</h4>
                  <p className="text-xs text-brand-100 mb-4">Please take 2 minutes to update your care team.</p>
                  <button className="w-full bg-white text-brand-700 py-2.5 rounded-xl text-sm font-bold">Start Check-in</button>
                </div>

                {/* Medications Mock */}
                <div className="px-2 mt-2">
                  <h4 className="text-sm font-bold text-ink-900 mb-3">Your Medicines</h4>
                  <div className="bg-white p-3 rounded-xl shadow-sm border border-ink-300/10 flex items-center gap-3">
                    <div className="bg-risk-low-bg text-risk-low p-2 rounded-lg">
                      <Pill size={16} />
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-bold text-ink-900">Amoxicillin</p>
                      <p className="text-[10px] text-ink-500">500mg · After meals</p>
                    </div>
                    <div className="h-5 w-5 rounded-full border-2 border-brand-500 bg-brand-500 flex items-center justify-center">
                      <CheckCircle2 size={12} className="text-white" />
                    </div>
                  </div>
                </div>
              </div>
              
              {/* Bottom Nav Mock */}
              <div className="h-16 w-full border-t border-ink-300/10 bg-white absolute bottom-0 left-0 right-0 flex justify-around items-center px-4 text-ink-400">
                <div className="flex flex-col items-center gap-1 text-brand-700">
                  <div className="h-5 w-5 bg-brand-700 rounded-sm opacity-20"></div>
                  <div className="w-8 h-1 bg-brand-700 rounded-full"></div>
                </div>
                <div className="h-5 w-5 bg-ink-300 rounded-sm opacity-20"></div>
                <div className="h-5 w-5 bg-ink-300 rounded-sm opacity-20"></div>
                <div className="h-5 w-5 bg-ink-300 rounded-sm opacity-20"></div>
              </div>
            </div>
          </div>
          
          <div className="lg:pl-8 lg:pt-4 order-1 lg:order-2">
            <div className="lg:max-w-lg">
              <h2 className="text-base font-semibold leading-7 text-brand-600 uppercase tracking-wider">For Patients</h2>
              <p className="mt-2 text-3xl font-bold tracking-tight text-ink-900 sm:text-4xl">
                Simple enough for every day.
              </p>
              <p className="mt-6 text-lg leading-8 text-ink-500">
                Patients receive a streamlined, mobile-first experience designed to make daily check-ins effortless and medication tracking clear.
              </p>
              
              <ul className="mt-8 space-y-4 text-ink-700">
                {['Complete daily check-ins easily', 'See today\'s required care', 'Review and check off medicines', 'Receive care team alerts', 'Track personal health progress'].map((item) => (
                  <li key={item} className="flex gap-x-3 items-center">
                    <CheckCircle2 className="h-5 w-5 flex-none text-brand-600" aria-hidden="true" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
