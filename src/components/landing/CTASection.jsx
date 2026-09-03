import React from "react";
import { useNavigate } from "react-router-dom";
import Button from "../ui/Button";
import { ArrowRight } from "lucide-react";

export default function CTASection() {
  const navigate = useNavigate();

  return (
    <section className="bg-brand-900 py-24 sm:py-32 text-center relative overflow-hidden">
      <div className="absolute inset-0 opacity-[0.05] bg-[radial-gradient(#ffffff_1px,transparent_1px)] [background-size:16px_16px]"></div>
      
      <div className="relative z-10 mx-auto max-w-3xl px-6 lg:px-8">
        <h2 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">
          Ready to stay connected beyond discharge?
        </h2>
        <p className="mt-6 text-lg leading-8 text-brand-100 mb-10">
          Choose your portal to continue.
        </p>
        
        <div className="flex flex-col sm:flex-row justify-center items-center gap-4">
          <Button 
            size="lg" 
            variant="secondary" 
            className="w-full sm:w-auto bg-white text-brand-900 hover:bg-brand-50 hover:text-brand-900 border-none"
            rightIcon={<ArrowRight size={18} />}
            onClick={() => navigate("/patient/login")}
          >
            Continue as Patient
          </Button>
          
          <Button 
            size="lg" 
            className="w-full sm:w-auto bg-brand-700 text-white hover:bg-brand-600 border border-brand-500"
            rightIcon={<ArrowRight size={18} />}
            onClick={() => navigate("/doctor/login")}
          >
            Continue as Doctor
          </Button>
        </div>
      </div>
    </section>
  );
}
