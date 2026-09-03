import React from "react";
import Button from "../ui/Button";
import { ArrowRight } from "lucide-react";
import RiskBadge from "../healthcare/RiskBadge";
import CheckinSummary from "../healthcare/CheckinSummary";

export default function Hero() {
  return (
    <section className="relative overflow-hidden bg-canvas pt-16 md:pt-24 lg:pt-32 pb-16">
      <div className="mx-auto max-w-7xl px-6 lg:px-8">
        <div className="grid gap-16 lg:grid-cols-2 lg:gap-8 items-center">
          <div className="max-w-2xl text-left">
            <p className="text-sm font-semibold uppercase tracking-wider text-brand-600">
              Connected Care, Beyond Discharge
            </p>
            <h1 className="mt-4 text-4xl font-bold tracking-tight text-ink-900 sm:text-6xl">
              Healthcare that stays with the patient.
            </h1>
            <p className="mt-6 text-lg leading-8 text-ink-700">
              HealBytes helps care teams monitor patients after discharge, identify emerging risks, coordinate follow-ups, and keep patients on track with their care.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-4">
              <a href="#role-selector">
                <Button size="lg">Get Started</Button>
              </a>
              <a href="#how-it-works">
                <Button variant="secondary" size="lg" rightIcon={<ArrowRight size={18} />}>
                  Explore HealBytes
                </Button>
              </a>
            </div>
          </div>
          
          <div className="relative mx-auto w-full max-w-lg lg:max-w-none">
            {/* Abstract UI representation */}
            <div className="relative rounded-2xl border border-ink-300/15 bg-white p-6 shadow-raised z-10">
              <div className="flex items-center justify-between border-b border-ink-300/10 pb-4">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-brand-50 text-brand-700 font-bold">
                    RS
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-ink-900">Rahul Sharma</h3>
                    <p className="text-xs text-ink-500">Post-Op Recovery</p>
                  </div>
                </div>
                <RiskBadge level="HIGH" />
              </div>
              <div className="py-4">
                <p className="text-xs font-semibold uppercase tracking-wide text-ink-400 mb-2">Latest Check-in</p>
                <div className="rounded-xl bg-risk-high-bg p-3 border border-risk-high/10">
                  <div className="flex justify-between items-start">
                    <div>
                      <p className="text-sm font-semibold text-risk-high">Chest Discomfort (Severe)</p>
                      <p className="text-xs text-ink-700 mt-1">Since yesterday · Missed one dose</p>
                    </div>
                  </div>
                </div>
              </div>
              <div className="border-t border-ink-300/10 pt-4 flex gap-2">
                <Button fullWidth size="sm">Review Patient</Button>
              </div>
            </div>
            
            {/* Background decorative elements */}
            <div className="absolute -top-6 -right-6 h-64 w-64 rounded-full bg-brand-100/50 blur-3xl -z-10"></div>
            <div className="absolute -bottom-10 -left-10 h-64 w-64 rounded-full bg-risk-medium-bg blur-3xl -z-10"></div>
          </div>
        </div>
      </div>
    </section>
  );
}
