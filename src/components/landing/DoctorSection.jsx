import React from "react";
import { CheckCircle2, ShieldQuestion } from "lucide-react";
import RiskScore from "../healthcare/RiskScore";
import RiskBadge from "../healthcare/RiskBadge";

export default function DoctorSection() {
  return (
    <section id="doctor-experience" className="overflow-hidden bg-canvas py-24 sm:py-32">
      <div className="mx-auto max-w-7xl px-6 lg:px-8">
        <div className="mx-auto grid max-w-2xl grid-cols-1 gap-x-16 gap-y-16 sm:gap-y-20 lg:mx-0 lg:max-w-none lg:grid-cols-2 lg:items-center">
          <div className="lg:pr-8 lg:pt-4">
            <div className="lg:max-w-lg">
              <h2 className="text-base font-semibold leading-7 text-brand-600 uppercase tracking-wider">For Doctors &amp; Care Teams</h2>
              <p className="mt-2 text-3xl font-bold tracking-tight text-ink-900 sm:text-4xl">
                See who needs attention.
              </p>
              <p className="mt-6 text-lg leading-8 text-ink-500">
                Care teams have a comprehensive dashboard highlighting patients who may need follow-up care based on their recent check-ins.
              </p>
              
              <ul className="mt-8 space-y-4 text-ink-700">
                {['Identify patients needing attention', 'Review AI-assisted risk insights', 'Schedule follow-up appointments', 'Monitor medication adherence', 'Manage care team alerts'].map((item) => (
                  <li key={item} className="flex gap-x-3 items-center">
                    <CheckCircle2 className="h-5 w-5 flex-none text-brand-600" aria-hidden="true" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <div className="relative">
            {/* Abstract UI representation of Doctor Dashboard */}
            <div className="relative w-full rounded-2xl border border-ink-300/15 bg-surface-muted p-6 sm:p-8 shadow-card overflow-hidden">
              <div className="flex justify-between items-center mb-6">
                <h3 className="text-lg font-bold text-ink-900">High Priority Alerts</h3>
                <span className="bg-risk-high text-white text-xs font-bold px-2 py-1 rounded-full">2 New</span>
              </div>
              
              <div className="space-y-4">
                {/* Alert Card 1 */}
                <div className="bg-white rounded-xl p-4 border border-ink-300/10 shadow-sm flex items-start gap-4">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-risk-high-bg text-risk-high">
                    <ShieldQuestion size={20} />
                  </div>
                  <div className="flex-1">
                    <div className="flex justify-between items-start">
                      <h4 className="text-sm font-bold text-ink-900">Priya Nair</h4>
                      <RiskBadge level="HIGH" size="sm" />
                    </div>
                    <p className="text-sm text-ink-700 mt-1">Increasing chest discomfort reported in recent check-in.</p>
                    <div className="mt-3 flex gap-2">
                      <button className="text-xs font-semibold text-brand-700 bg-brand-50 px-3 py-1.5 rounded-lg border border-brand-200">Review Patient</button>
                    </div>
                  </div>
                </div>

                {/* Alert Card 2 */}
                <div className="bg-white rounded-xl p-4 border border-ink-300/10 shadow-sm flex items-start gap-4 opacity-75">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-risk-medium-bg text-risk-medium">
                    <ShieldQuestion size={20} />
                  </div>
                  <div className="flex-1">
                    <div className="flex justify-between items-start">
                      <h4 className="text-sm font-bold text-ink-900">Arjun Mehta</h4>
                      <RiskBadge level="MEDIUM" size="sm" />
                    </div>
                    <p className="text-sm text-ink-700 mt-1">Missed medication for 2 consecutive days.</p>
                  </div>
                </div>
              </div>

              {/* Decorative Fade */}
              <div className="absolute bottom-0 left-0 right-0 h-24 bg-gradient-to-t from-surface-muted to-transparent pointer-events-none"></div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
