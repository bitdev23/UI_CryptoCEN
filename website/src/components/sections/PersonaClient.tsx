"use client";

import { motion } from "framer-motion";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { Sparkles, ArrowRight, CheckCircle2, Target, Zap } from "lucide-react";
import Link from "next/link";
import { MagneticButton } from "@/components/ui/MagneticButton";

interface PersonaConfig {
  title: string;
  subtitle: string;
  pain: string;
  solution: string;
  features: string[];
  cta: string;
  color: string;
}

const personaData: Record<string, PersonaConfig> = {
  founders: {
    title: "The Authority Engine for Founders",
    subtitle: "Scale your personal brand without the 20-hour work week.",
    pain: "You have the vision, but not the time. Your LinkedIn is silent while your competitors own the narrative.",
    solution: "Velank AI turns your internal strategy docs and voice notes into an undeniable LinkedIn presence. High authority. Zero manual writing.",
    features: [
      "Digital Twin Voice Calibration",
      "Confidential Knowledge Base",
      "Executive Content Pipeline",
      "Inbound Lead Tracking"
    ],
    cta: "Build My Founder Authority",
    color: "from-indigo-600 to-blue-500"
  },
  consultants: {
    title: "The Inbound Machine for Consultants",
    subtitle: "Turn your methodology into trust-building content on autopilot.",
    pain: "Selling your 'time' is hard. Selling your 'thinking' is where the scale is. But writing every day is a grind.",
    solution: "Upload your frameworks and case studies once. Velank AI extracts the 'Atomic Insights' and builds your reputation as the go-to expert in your niche.",
    features: [
      "Methodology Extraction",
      "Case Study Atomizer",
      "Trust-Based Hook Library",
      "Relationship-First Scheduling"
    ],
    cta: "Scale My Consulting Practice",
    color: "from-emerald-600 to-teal-500"
  },
  coaches: {
    title: "The Audience Engine for Coaches",
    subtitle: "Build a high-trust community while you focus on your clients.",
    pain: "You're great at coaching, but 'content creator' wasn't in the job description. Generic AI makes you look like a commodity.",
    solution: "Scale your unique philosophy. Velank AI ensures every post sounds like you, feels like you, and converts like you—even when you're coaching.",
    features: [
      "Voice-Matched Drafting",
      "Empathy-First Templates",
      "Viral Growth Hooks",
      "Community Engagement Analytics"
    ],
    cta: "Grow My Coaching Brand",
    color: "from-amber-500 to-orange-600"
  },
  agencies: {
    title: "The Scale Engine for Agencies",
    subtitle: "Scale your ghostwriting offerings to 10x more clients.",
    pain: "Hiring copywriters is expensive. Maintaining 20 different executive voices manually is impossible to scale.",
    solution: "The first AI platform built for agencies. Maintain infinite 'Digital Twins' for your clients, each grounded in their specific proprietary knowledge.",
    features: [
      "Multi-Client Workspaces",
      "Infinite Digital Twins",
      "White-Label Ready Analytics",
      "Client Approval Workflow"
    ],
    cta: "Scale My Agency Revenue",
    color: "from-purple-600 to-[#6E56CF]"
  }
};

export function PersonaClient({ persona }: { persona: string }) {
  const data = personaData[persona] || personaData.founders;

  return (
    <div className="min-h-screen bg-white text-zinc-900 font-sans selection:bg-indigo-100 selection:text-indigo-900">
      <Header />
      
      <main className="pt-32 pb-20">
        {/* Dynamic Hero Section */}
        <section className="relative py-20 overflow-hidden">
          <div className="absolute top-0 right-0 w-[600px] h-[600px] bg-zinc-50 rounded-full blur-[120px] pointer-events-none -translate-y-1/2 translate-x-1/2 opacity-60" />
          <div className="container mx-auto px-6 max-w-6xl relative z-10">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="max-w-4xl mx-auto text-center"
            >
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-zinc-100 border border-zinc-200 text-[10px] font-bold tracking-[0.2em] uppercase text-zinc-600 mb-8 shadow-sm">
                <Sparkles className="w-3.5 h-3.5 text-indigo-500" /> Velank AI for {persona}
              </div>
              <h1 className="text-5xl md:text-7xl font-black tracking-tighter mb-8 leading-[1.1] text-zinc-900">
                {data.title.split("for")[0]} for <br/> 
                <span className={`text-transparent bg-clip-text bg-gradient-to-r ${data.color} italic font-serif`}>
                  {persona.charAt(0).toUpperCase() + persona.slice(1)}.
                </span>
              </h1>
              <p className="text-xl md:text-2xl text-zinc-500 mb-12 font-medium leading-relaxed max-w-3xl mx-auto">
                {data.subtitle}
              </p>
              
              <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                <MagneticButton>
                  <Link href="https://app.velank.io/login" className={`inline-flex items-center justify-center rounded-2xl font-black transition-all bg-gradient-to-r ${data.color} text-white h-16 px-10 text-lg shadow-xl hover:opacity-90 active:scale-95 group`}>
                    {data.cta} <ArrowRight className="ml-2 w-5 h-5 group-hover:translate-x-1 transition-transform" />
                  </Link>
                </MagneticButton>
                <Link href="#how-it-works" className="text-zinc-500 font-bold hover:text-zinc-900 transition-colors px-6 py-4">
                  How it works &rarr;
                </Link>
              </div>
            </motion.div>
          </div>
        </section>

        {/* The Pain vs Solution Section */}
        <section className="py-32 bg-zinc-50 border-y border-zinc-100">
          <div className="container mx-auto px-6 max-w-6xl">
            <div className="grid md:grid-cols-2 gap-16 md:gap-24 items-center">
              <div>
                <div className="w-12 h-12 bg-red-50 rounded-xl flex items-center justify-center border border-red-100 mb-8">
                   <Target className="w-6 h-6 text-red-600" />
                </div>
                <h2 className="text-3xl md:text-5xl font-black text-zinc-900 mb-8 tracking-tighter">The Brutal Truth.</h2>
                <p className="text-lg text-zinc-600 leading-relaxed font-medium">
                  {data.pain}
                </p>
              </div>
              <div className="bg-white rounded-[3rem] p-8 md:p-12 shadow-2xl shadow-zinc-200 border border-zinc-100 relative group">
                <div className="absolute -top-6 -right-6 w-24 h-24 bg-indigo-500/10 rounded-full blur-2xl group-hover:scale-150 transition-transform duration-700" />
                <div className="w-12 h-12 bg-indigo-50 rounded-xl flex items-center justify-center border border-indigo-100 mb-8">
                   <Zap className="w-6 h-6 text-indigo-600" />
                </div>
                <h3 className="text-2xl font-black text-zinc-900 mb-6 tracking-tight">The Velank Solution.</h3>
                <p className="text-zinc-600 leading-relaxed font-medium mb-8">
                  {data.solution}
                </p>
                <div className="space-y-4">
                  {data.features.map((f: string, i: number) => (
                    <div key={i} className="flex items-center gap-3 text-zinc-900 font-bold">
                       <CheckCircle2 className="w-5 h-5 text-indigo-500" />
                       {f}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Dynamic CTA Band */}
        <section className={`py-24 bg-gradient-to-r ${data.color} relative overflow-hidden`}>
          <div className="absolute inset-0 bg-white/10 opacity-20 pointer-events-none" />
          <div className="container mx-auto px-6 max-w-4xl text-center relative z-10">
            <h2 className="text-4xl md:text-6xl font-black text-white mb-10 tracking-tighter">
              Ready to win back your time?
            </h2>
            <Link href="https://app.velank.io/login" className="inline-flex items-center justify-center rounded-2xl bg-white text-zinc-900 h-16 px-12 text-xl font-black shadow-2xl hover:bg-zinc-50 active:scale-95 transition-all group">
               Get Your First Post Free <ArrowRight className="ml-2 w-5 h-5 group-hover:translate-x-1 transition-transform" />
            </Link>
            <p className="mt-8 text-white/80 font-bold uppercase tracking-widest text-xs">
              No credit card required • Works with your existing LinkedIn
            </p>
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
}
