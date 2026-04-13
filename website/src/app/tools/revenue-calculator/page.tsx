"use client";

import { motion } from "framer-motion";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { InteractiveGrid } from "@/components/ui/InteractiveGrid";
import { RevenueCalculator } from "@/components/ui/RevenueCalculator";
import { Sparkles, ArrowRight, HelpCircle } from "lucide-react";
import Link from "next/link";

export default function ROICalculatorPage() {
  return (
    <div className="min-h-screen bg-white text-zinc-900 relative flex flex-col pt-28 font-sans overflow-hidden">
      <Header />
      
      {/* 1. Hero Section */}
      <section className="pt-24 pb-32 relative border-b border-zinc-100 overflow-hidden">
        <InteractiveGrid />
        <div className="absolute top-0 right-0 w-[600px] h-[600px] bg-indigo-50/50 rounded-full blur-[120px] pointer-events-none -translate-y-1/2 translate-x-1/3" />
        
        <div className="container mx-auto px-6 relative z-10 max-w-6xl text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7 }}
          >
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-50 border border-indigo-100 text-[10px] font-bold tracking-widest uppercase text-indigo-600 mb-8 shadow-sm">
              <Sparkles className="w-3.5 h-3.5" /> ROI Calculator
            </div>

            <h1 className="text-4xl md:text-7xl font-black tracking-tight mb-8 text-zinc-900 leading-[1.1] px-2">
              Stop guessing. <br className="hidden md:block" />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-600 to-[#8C7BFF]">
                Calculate your upside.
              </span>
            </h1>
            
            <p className="text-xl md:text-2xl text-zinc-600 mb-12 max-w-3xl mx-auto font-medium leading-relaxed">
              Use our interactive estimator to see exactly how much your internal expertise is worth when you turn it into a consistent LinkedIn pipeline.
            </p>
          </motion.div>
        </div>
      </section>

      {/* 2. Calculator Section */}
      <section className="py-24 bg-zinc-50/50 relative">
        <div className="container mx-auto px-6 max-w-6xl">
          <RevenueCalculator />
          
          <div className="mt-16 grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="flex flex-col gap-4">
              <div className="w-10 h-10 rounded-xl bg-white border border-zinc-200 flex items-center justify-center shadow-sm">
                <HelpCircle className="w-5 h-5 text-indigo-600" />
              </div>
              <h4 className="text-lg font-bold">Why Average Deal Value?</h4>
              <p className="text-sm text-zinc-500 font-medium leading-relaxed">LinkedIn is the #1 platform for high-ticket B2B deals. Even a single extra deal per year can 10x your investment in authority branding.</p>
            </div>
            <div className="flex flex-col gap-4">
              <div className="w-10 h-10 rounded-xl bg-white border border-zinc-200 flex items-center justify-center shadow-sm">
                <HelpCircle className="w-5 h-5 text-indigo-600" />
              </div>
              <h4 className="text-lg font-bold">What is Efficiency Value?</h4>
              <p className="text-sm text-zinc-500 font-medium leading-relaxed">It takes most founders 3-4 hours to write a strategic post. Velank AI reduces this to under 10 minutes, giving you 150+ hours back per year.</p>
            </div>
            <div className="flex flex-col gap-4">
              <div className="w-10 h-10 rounded-xl bg-white border border-zinc-200 flex items-center justify-center shadow-sm">
                <HelpCircle className="w-5 h-5 text-indigo-600" />
              </div>
              <h4 className="text-lg font-bold">Conservative Estimations</h4>
              <p className="text-sm text-zinc-500 font-medium leading-relaxed">Our ROI model uses conservative industry benchmarks. Many users report seeing a 2.4x increase in inbound velocity within 90 days.</p>
            </div>
          </div>
        </div>
      </section>

      {/* 3. Final Conversion Section */}
      <section className="py-32 bg-white relative">
        <div className="container mx-auto px-6 max-w-4xl text-center">
          <h2 className="text-3xl md:text-5xl font-black mb-8 tracking-tight">Ready to claim your upside?</h2>
          <p className="text-xl text-zinc-500 mb-12 font-medium">
            Velank AI starts at $0. No credit card required. Build your authority today.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link href="https://app.velank.io/login" className="px-10 py-5 bg-indigo-600 text-white rounded-2xl font-black text-xl shadow-xl hover:bg-indigo-700 transition-all flex items-center gap-2 group">
              Start Building Now <ArrowRight className="w-6 h-6 group-hover:translate-x-1 transition-transform" />
            </Link>
            <Link href="/audit" className="px-10 py-5 bg-white text-indigo-600 border border-indigo-100 rounded-2xl font-bold text-xl hover:bg-zinc-50 transition-all">
              Get an Audit first
            </Link>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
}
