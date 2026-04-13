"use client";

import React, { useState, useRef } from "react";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { motion, AnimatePresence } from "framer-motion";
import { 
  Sparkles, 
  ArrowRight, 
  Camera, 
  Layout, 
  CheckCircle2, 
  ShieldCheck, 
  Zap, 
  Share2,
  Download,
  Info
} from "lucide-react";
import Link from "next/link";
import { MagneticButton } from "@/components/ui/MagneticButton";

export default function ProfileMockupGenerator() {
  const [name, setName] = useState("");
  const [headline, setHeadline] = useState("");
  const [company, setCompany] = useState("");
  const [isGenerated, setIsGenerated] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  
  const handleGenerate = () => {
    if (!name || !headline) return;
    setIsGenerating(true);
    setTimeout(() => {
      setIsGenerated(true);
      setIsGenerating(false);
    }, 1500);
  };

  const reset = () => {
    setIsGenerated(false);
    setName("");
    setHeadline("");
    setCompany("");
  };

  return (
    <div className="min-h-screen bg-zinc-50 text-zinc-900 font-sans selection:bg-indigo-500/30">
      <Header />
      
      <main className="pt-32 pb-20">
        <div className="container mx-auto px-6 max-w-6xl relative">
          
          {/* Header Section */}
          <div className="text-center mb-16">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-50 border border-indigo-100 text-[10px] font-bold tracking-[0.2em] uppercase text-indigo-600 mb-6 shadow-sm"
            >
              <Layout className="w-3.5 h-3.5" /> Identity Visualizer
            </motion.div>
            <h1 className="text-4xl md:text-6xl font-black tracking-tighter mb-6 text-zinc-900 leading-tight">
              See your <span className="italic text-indigo-600">Billion-Dollar</span> <br/> LinkedIn Profile.
            </h1>
            <p className="text-lg text-zinc-500 max-w-2xl mx-auto font-medium leading-relaxed">
              Stop guessing how you look to high-ticket clients. Enter your details to visualize your authority upgrade in 60 seconds.
            </p>
          </div>

          <div className="grid lg:grid-cols-12 gap-12 items-start">
            
            {/* Input Side */}
            <div className="lg:col-span-5">
              <div className="bg-white border border-zinc-200 rounded-[2.5rem] p-8 md:p-10 shadow-xl shadow-zinc-200/50 relative overflow-hidden">
                <div className="absolute top-0 right-0 w-32 h-32 bg-indigo-50 rounded-full blur-[60px] opacity-50 -translate-y-1/2 translate-x-1/2" />
                
                <div className="space-y-6 relative z-10">
                  <div>
                    <label className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest block mb-2 px-1">Full Name</label>
                    <input 
                      type="text" 
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder="e.g. Marcus Thorne"
                      className="w-full bg-zinc-50 border border-zinc-100 rounded-2xl px-6 py-4 font-bold text-zinc-900 placeholder:text-zinc-300 focus:outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500/30 transition-all"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest block mb-2 px-1">Current Headline</label>
                    <textarea 
                      value={headline}
                      onChange={(e) => setHeadline(e.target.value)}
                      placeholder="e.g. Founder of Nexus | Building high-scale SaaS"
                      rows={3}
                      className="w-full bg-zinc-50 border border-zinc-100 rounded-2xl px-6 py-4 font-bold text-zinc-900 placeholder:text-zinc-300 focus:outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500/30 transition-all resize-none"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest block mb-2 px-1">Company (Optional)</label>
                    <input 
                      type="text" 
                      value={company}
                      onChange={(e) => setCompany(e.target.value)}
                      placeholder="e.g. Nexus Architecture"
                      className="w-full bg-zinc-50 border border-zinc-100 rounded-2xl px-6 py-4 font-bold text-zinc-900 placeholder:text-zinc-300 focus:outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500/30 transition-all"
                    />
                  </div>

                  <MagneticButton>
                    <button 
                      onClick={handleGenerate}
                      disabled={isGenerating || !name || !headline}
                      className="w-full flex items-center justify-center gap-2 px-8 py-5 bg-zinc-900 text-white rounded-2xl font-black text-lg shadow-2xl hover:bg-black transition-all disabled:opacity-50 disabled:cursor-not-allowed group"
                    >
                      {isGenerating ? "Simulating Reality..." : "Generate My Billion-Dollar Mockup"}
                      {!isGenerating && <Sparkles className="w-5 h-5 group-hover:rotate-12 transition-transform" />}
                    </button>
                  </MagneticButton>

                  <div className="flex items-center gap-3 pt-4 border-t border-zinc-100 mt-8">
                    <div className="w-8 h-8 rounded-lg bg-emerald-50 flex items-center justify-center border border-emerald-100">
                      <ShieldCheck className="w-4 h-4 text-emerald-600" />
                    </div>
                    <p className="text-[10px] font-bold text-zinc-400 leading-tight uppercase tracking-tight">
                      Privacy Protected • Zero Login Required • Instant Visual
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* Output Side (Mockup) */}
            <div className="lg:col-span-7 relative min-h-[500px]">
              <AnimatePresence mode="wait">
                {!isGenerated ? (
                  <motion.div 
                    key="empty"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="absolute inset-0 flex flex-col items-center justify-center p-12 text-center"
                  >
                    <div className="w-24 h-24 rounded-full bg-zinc-100 border-2 border-dashed border-zinc-200 flex items-center justify-center mb-6 text-zinc-300">
                      <Camera className="w-10 h-10" />
                    </div>
                    <h3 className="text-2xl font-bold text-zinc-300">Your mockup will appear here</h3>
                    <p className="text-zinc-400 mt-2 font-medium">Add your details to start the simulation.</p>
                  </motion.div>
                ) : (
                  <motion.div
                    key="mockup"
                    initial={{ opacity: 0, scale: 0.9, y: 20 }}
                    animate={{ opacity: 1, scale: 1, y: 0 }}
                    className="space-y-8"
                  >
                    {/* The LinkedIn Mockup Card */}
                    <div className="bg-white border border-zinc-200 rounded-[2.5rem] overflow-hidden shadow-2xl shadow-indigo-100 relative group">
                      
                      {/* Premium Banner */}
                      <div className="h-44 md:h-56 relative bg-zinc-900 overflow-hidden">
                        <div className="absolute inset-0 bg-brand-mesh opacity-30" />
                        <div className="absolute inset-0 bg-gradient-to-br from-indigo-600/40 via-transparent to-black/60" />
                        <div className="absolute bottom-6 left-8 right-8 flex justify-between items-end">
                          <div className="space-y-1">
                            <div className="text-white font-black text-2xl md:text-3xl tracking-tighter drop-shadow-md">
                              {company || "THE INDUSTRY STANDARD"}
                            </div>
                            <div className="text-indigo-200 font-bold text-xs uppercase tracking-[0.3em] opacity-80 drop-shadow-sm">
                              AUTHORITY PARTNER SINCE 2026
                            </div>
                          </div>
                          <div className="hidden md:block">
                             <div className="flex gap-2">
                               {[1, 2, 3].map(i => <div key={i} className="w-10 h-1 bg-white/20 rounded-full" />)}
                             </div>
                          </div>
                        </div>
                      </div>

                      {/* Profile Section */}
                      <div className="px-8 pb-10 relative">
                        {/* Avatar */}
                        <div className="w-32 h-32 md:w-40 md:h-40 rounded-full bg-white border-4 border-white shadow-xl -mt-16 md:-mt-20 overflow-hidden relative z-10">
                          <div className="absolute inset-0 bg-zinc-100 flex items-center justify-center text-zinc-300">
                             <Camera className="w-12 h-12" />
                          </div>
                        </div>

                        {/* Details */}
                        <div className="mt-6">
                           <div className="flex items-center gap-3 mb-2">
                             <h4 className="text-3xl font-black text-zinc-900 tracking-tight">{name}</h4>
                             <CheckCircle2 className="w-6 h-6 text-indigo-500 fill-indigo-50 opacity-100" />
                           </div>
                           <p className="text-lg text-zinc-600 font-bold leading-snug max-w-xl group-hover:text-indigo-600 transition-colors duration-500">
                             {headline.length > 80 ? headline : headline + " | Predicting the next $100M infrastructure shift."}
                           </p>
                           <p className="text-sm text-zinc-400 mt-4 flex items-center gap-2 font-medium">
                             Dubai, United Arab Emirates • <button className="text-indigo-600 font-bold hover:underline">Contact info</button>
                           </p>
                           <p className="text-sm text-indigo-600 font-bold mt-2 hover:underline cursor-pointer">
                              24,402 followers • 500+ connections
                           </p>
                        </div>

                        {/* Action Buttons Mockup */}
                        <div className="flex flex-wrap gap-3 mt-8">
                           <div className="px-6 py-2.5 bg-indigo-600 text-white rounded-full font-black text-sm shadow-lg shadow-indigo-600/20">Follow</div>
                           <div className="px-6 py-2.5 border-2 border-indigo-600 text-indigo-600 rounded-full font-black text-sm hover:bg-indigo-50 transition-colors">Message</div>
                           <div className="px-6 py-2.5 border-2 border-zinc-200 text-zinc-500 rounded-full font-black text-sm hover:border-zinc-300 transition-colors">More</div>
                        </div>
                      </div>

                      {/* CTA Overlay Preach */}
                      <div className="absolute top-4 right-4 z-20">
                         <div className="bg-emerald-500 text-white text-[10px] font-black uppercase tracking-widest px-3 py-1 rounded-full shadow-lg flex items-center gap-1">
                           <Zap className="w-3 h-3" /> Potential 12% Conversion Lift
                         </div>
                      </div>
                    </div>

                    {/* Funnel Section */}
                    <div className="bg-indigo-600 rounded-[2.5rem] p-8 md:p-12 text-white relative overflow-hidden shadow-2xl">
                       <div className="absolute top-0 right-0 w-64 h-64 bg-white/10 rounded-full blur-[80px] -translate-y-1/2 translate-x-1/2" />
                       <div className="relative z-10 flex flex-col md:flex-row items-center gap-8 justify-between">
                          <div className="text-center md:text-left">
                             <h5 className="text-2xl font-black mb-2 tracking-tight">Your current profile is leaking leads.</h5>
                             <p className="text-indigo-100 font-medium opacity-80">This mockup is just the visual. We have the actual copy ready for you.</p>
                          </div>
                          <div className="shrink-0 space-y-4 w-full md:w-auto">
                            <Link href="/audit" className="w-full flex items-center justify-center gap-2 px-8 py-4 bg-white text-zinc-900 rounded-2xl font-black shadow-xl hover:bg-zinc-50 transition-all group">
                               Get My Professional Audit ($19) <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                            </Link>
                            <button onClick={reset} className="w-full text-indigo-200 text-xs font-bold uppercase tracking-widest hover:text-white transition-colors">
                               Edit Details
                            </button>
                          </div>
                       </div>
                    </div>

                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                       {[
                         { icon: Download, label: "Export Mockup" },
                         { icon: Share2, label: "Share Result" },
                         { icon: Sparkles, label: "AI Suggestions" },
                         { icon: Info, label: "Why this works" }
                       ].map((item, i) => (
                         <div key={i} className="cursor-not-allowed opacity-50 p-4 rounded-2xl border border-zinc-200 bg-white flex flex-col items-center gap-2 hover:bg-zinc-50 transition-colors">
                           <item.icon className="w-5 h-5 text-zinc-400" />
                           <span className="text-[10px] font-black uppercase tracking-widest text-zinc-400">{item.label}</span>
                         </div>
                       ))}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}
