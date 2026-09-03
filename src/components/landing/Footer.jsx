import React from "react";
import { HeartPulse } from "lucide-react";
import { Link } from "react-router-dom";

export default function Footer() {
  const navigation = {
    product: [
      { name: "How it works", href: "#how-it-works" },
      { name: "Features", href: "#features" },
      { name: "Patient Care", href: "#patient-experience" },
      { name: "Care Team", href: "#doctor-experience" },
    ],
    portals: [
      { name: "Patient Login", href: "/patient/login", isRoute: true },
      { name: "Doctor Login", href: "/doctor/login", isRoute: true },
    ],
    information: [
      { name: "About HealBytes", href: "#about" },
    ],
  };

  return (
    <footer className="bg-canvas border-t border-ink-300/20" aria-labelledby="footer-heading">
      <h2 id="footer-heading" className="sr-only">Footer</h2>
      <div className="mx-auto max-w-7xl px-6 pb-8 pt-16 sm:pt-24 lg:px-8 lg:pt-32">
        <div className="xl:grid xl:grid-cols-3 xl:gap-8">
          <div className="space-y-8">
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-700 text-white">
                <HeartPulse size={18} />
              </div>
              <span className="text-xl font-bold text-ink-900">HealBytes</span>
            </div>
            <p className="text-sm leading-6 text-ink-600">
              AI-assisted healthcare coordination and follow-up.
            </p>
          </div>
          
          <div className="mt-16 grid grid-cols-2 gap-8 xl:col-span-2 xl:mt-0">
            <div className="md:grid md:grid-cols-2 md:gap-8">
              <div>
                <h3 className="text-sm font-semibold leading-6 text-ink-900">Product</h3>
                <ul role="list" className="mt-6 space-y-4">
                  {navigation.product.map((item) => (
                    <li key={item.name}>
                      <a href={item.href} className="text-sm leading-6 text-ink-500 hover:text-ink-900">
                        {item.name}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
              <div className="mt-10 md:mt-0">
                <h3 className="text-sm font-semibold leading-6 text-ink-900">Portals</h3>
                <ul role="list" className="mt-6 space-y-4">
                  {navigation.portals.map((item) => (
                    <li key={item.name}>
                      {item.isRoute ? (
                        <Link to={item.href} className="text-sm leading-6 text-ink-500 hover:text-ink-900">
                          {item.name}
                        </Link>
                      ) : (
                        <a href={item.href} className="text-sm leading-6 text-ink-500 hover:text-ink-900">
                          {item.name}
                        </a>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
            <div className="md:grid md:grid-cols-2 md:gap-8">
              <div>
                <h3 className="text-sm font-semibold leading-6 text-ink-900">Information</h3>
                <ul role="list" className="mt-6 space-y-4">
                  {navigation.information.map((item) => (
                    <li key={item.name}>
                      <a href={item.href} className="text-sm leading-6 text-ink-500 hover:text-ink-900">
                        {item.name}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </div>
        <div className="mt-16 border-t border-ink-300/10 pt-8 sm:mt-20 lg:mt-24">
          <p className="text-xs leading-5 text-ink-400">
            &copy; 2026 HealBytes. Built for connected healthcare.
          </p>
        </div>
      </div>
    </footer>
  );
}
