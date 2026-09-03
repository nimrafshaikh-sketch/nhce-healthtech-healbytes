import React from "react";
import { BrainCircuit, ArrowDown } from "lucide-react";

export default function AISection() {
  return (
    <section className="bg-brand-900 py-24 sm:py-32 text-white relative overflow-hidden">
      {/* Subtle background pattern */}
      <div className="absolute inset-0 opacity-[0.03] bg-[radial-gradient(#ffffff_1px,transparent_1px)] [background-size:16px_16px]"></div>
      
      <div className="mx-auto max-w-7xl px-6 lg:px-8 relative z-10">
        <div className="mx-auto max-w-2xl text-center">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-800 border border-brand-700/50 mb-6 shadow-xl">
            <BrainCircuit size={32} className="text-brand-300" />
          </div>
          <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
            Intelligence where it matters.
          </h2>
          <p className="mt-6 text-lg leading-8 text-brand-100">
            HealBytes analyzes patient check-ins and relevant care information to help identify changes that may require attention. It acts as an AI-assisted decision support system for care teams.
          </p>
        </div>

        <div className="mx-auto mt-16 max-w-3xl">
          <div className="rounded-3xl border border-brand-700 bg-brand-800/50 p-8 backdrop-blur-sm">
            <div className="grid gap-8 sm:grid-cols-3 items-center text-center">
              
              {/* Input */}
              <div className="flex flex-col gap-2">
                <div className="text-sm font-semibold uppercase tracking-wider text-brand-300 mb-2">Patient Inputs</div>
                <div className="bg-brand-900/80 rounded-xl p-3 text-sm border border-brand-700/50">Symptoms &amp; Severity</div>
                <div className="bg-brand-900/80 rounded-xl p-3 text-sm border border-brand-700/50">Duration</div>
                <div className="bg-brand-900/80 rounded-xl p-3 text-sm border border-brand-700/50">Medication Adherence</div>
              </div>

              {/* Engine */}
              <div className="flex flex-col items-center justify-center gap-4">
                <ArrowDown className="text-brand-500 sm:-rotate-90 sm:hidden block" size={24} />
                <div className="hidden sm:block text-brand-500">
                  <svg width="60" height="24" viewBox="0 0 60 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M0 12H58M58 12L48 2M58 12L48 22" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </div>
                
                <div className="h-16 w-16 rounded-full bg-brand-600 flex items-center justify-center shadow-lg border-2 border-brand-400">
                  <BrainCircuit size={24} className="text-white" />
                </div>
                
                <ArrowDown className="text-brand-500 sm:-rotate-90 sm:hidden block" size={24} />
                <div className="hidden sm:block text-brand-500">
                  <svg width="60" height="24" viewBox="0 0 60 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M0 12H58M58 12L48 2M58 12L48 22" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </div>
              </div>

              {/* Output */}
              <div className="flex flex-col gap-2">
                <div className="text-sm font-semibold uppercase tracking-wider text-brand-300 mb-2">AI Output</div>
                <div className="bg-risk-high-bg text-risk-high rounded-xl p-3 text-sm font-bold border border-risk-high/20">Risk Assessment</div>
                <div className="bg-brand-900/80 rounded-xl p-3 text-sm border border-brand-700/50">Care Team Notification</div>
                <div className="bg-brand-900/80 rounded-xl p-3 text-sm border border-brand-700/50">Follow-up Action</div>
              </div>

            </div>
          </div>
          
          <p className="mt-8 text-center text-xs text-brand-300">
            * HealBytes provides decision support and does not independently diagnose diseases.
          </p>
        </div>
      </div>
    </section>
  );
}
