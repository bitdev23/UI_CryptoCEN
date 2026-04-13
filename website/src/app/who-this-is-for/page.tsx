"use client";

import { motion } from "framer-motion";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { InteractiveGrid } from "@/components/ui/InteractiveGrid";
import { MagneticButton } from "@/components/ui/MagneticButton";
import Link from "next/link";
import { Users, Target, ArrowRight, CheckCircle2, TrendingUp } from "lucide-react";
import Image from "next/image";

export default function WhoThisIsFor() {
  return (
    <div className="min-h-screen bg-zinc-50 text-zinc-900 relative flex flex-col pt-28 font-sans overflow-hidden">
      <Header />
      
      {/* Hero Section */}
      <section className="pt-24 pb-32 relative border-b border-zinc-200 overflow-hidden">
        <InteractiveGrid />
        <div className="absolute top-0 right-0 w-[600px] h-[600px] bg-indigo-100 rounded-full blur-[120px] pointer-events-none -translate-y-1/2 translate-x-1/3 opacity-40" />
        <div className="absolute top-1/2 left-0 w-[400px] h-[400px] bg-blue-50 rounded-full blur-[100px] pointer-events-none -translate-y-1/2 -translate-x-1/3 opacity-40" />
        
        <div className="container mx-auto px-6 relative z-10 max-w-5xl text-center">
           <motion.div
             initial={{ opacity: 0, y: 30 }}
             animate={{ opacity: 1, y: 0 }}
             transition={{ duration: 0.7, ease: "easeOut" }}
           >
             <div className="inline-flex items-center justify-center gap-2 px-3 py-1 rounded-full bg-indigo-50 border border-indigo-100 text-[10px] font-bold tracking-widest uppercase text-indigo-600 mb-8 shadow-sm">
                <Users className="w-3.5 h-3.5" /> Personas & Archetypes
             </div>
             <h1 className="text-4xl md:text-6xl lg:text-7xl font-extrabold tracking-tight mb-8 text-zinc-900 drop-shadow-sm leading-[1.1] px-2">
               Built for people who have <br className="hidden md:block" />
               <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-600 to-blue-500">
                  something worth saying.
               </span>
             </h1>
             <p className="text-xl md:text-2xl text-zinc-600 mb-12 max-w-3xl mx-auto font-medium leading-relaxed">
               Whoever you are, visibility drives growth. Velank AI works for any professional where showing up consistently on LinkedIn fundamentally changes business outcomes.
             </p>
             
             <div className="flex justify-center">
               <MagneticButton>
                 <Link href="https://app.velank.io/login" className="inline-flex items-center justify-center rounded-xl font-bold transition-all focus:outline-none focus:ring-4 focus:ring-indigo-500/20 bg-gradient-to-b from-[#818CF8] to-[#6E56CF] text-white hover:from-[#9B8CFF] hover:to-[#7760EA] h-14 px-6 md:px-8 text-base md:text-lg shadow-xl shadow-[#6E56CF]/30 transform active:scale-95 group">
                    Build Your Authority System <ArrowRight className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" />
                 </Link>
               </MagneticButton>
             </div>
           </motion.div>
        </div>
      </section>

      {/* Personas Section - Hyper-Premium Bento Style */}
      <section className="py-32 bg-white relative overflow-hidden">
        <div className="container mx-auto px-6 max-w-7xl relative z-10">
          <div className="flex flex-col md:flex-row md:items-end justify-between gap-8 mb-20">
            <div className="max-w-2xl">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-50 border border-indigo-100 text-[10px] font-bold tracking-widest uppercase text-indigo-600 mb-6">
                <Target className="w-3.5 h-3.5" /> Market Fit
              </div>
              <h2 className="text-4xl md:text-6xl font-bold text-zinc-900 tracking-tighter leading-tight">
                The content engine for <br/> 
                <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-600 to-[#818CF8]">high-stakes players.</span>
              </h2>
            </div>
            <p className="text-lg text-zinc-500 max-w-sm font-medium leading-relaxed md:mb-2">
              Velank AI doesn&apos;t just write posts. It translates your professional worth into social capital.
            </p>
          </div>
           
          <div className="grid grid-cols-1 md:grid-cols-6 lg:grid-cols-12 gap-4">
            {/* Persona 1: Founder - Large Featured Card */}
            <motion.div 
               initial={{ opacity: 0, y: 20 }}
               whileInView={{ opacity: 1, y: 0 }}
               viewport={{ once: true }}
               className="md:col-span-6 lg:col-span-8 bg-white border border-zinc-200 rounded-[2.5rem] p-6 sm:p-10 relative overflow-hidden group min-h-[380px] md:min-h-[400px] flex flex-col justify-between shadow-sm hover:shadow-xl hover:border-indigo-100 transition-all duration-500"
            >
              <div className="absolute top-0 right-0 w-full h-full bg-[url('https://res.cloudinary.com/dzbcnwqut/image/upload/v1703649553/grid_q29nt2.svg')] opacity-[0.03] pointer-events-none" />
              <div className="absolute -right-20 -top-20 w-80 h-80 bg-indigo-100 rounded-full blur-[100px] pointer-events-none group-hover:bg-indigo-200/50 transition-colors" />
              
              <div className="relative z-10">
                <div className="w-14 h-14 bg-indigo-600 rounded-2xl flex items-center justify-center text-3xl mb-8 shadow-lg shadow-indigo-600/20">🚀</div>
                <h4 className="text-3xl md:text-4xl font-bold mb-4 tracking-tight text-zinc-900">The Founder</h4>
                <p className="text-zinc-600 text-xl max-w-md leading-relaxed mb-8 font-medium">
                  You have the vision, but zero bandwidth. We turn your service decks and wins into a 24/7 authority presence.
                </p>
              </div>
              
              <div className="relative z-10 flex flex-col sm:flex-row gap-6 items-start sm:items-center border-t border-zinc-100 pt-8 mt-12">
                <div className="flex -space-x-3">
                  {[1,2,3].map(i => (
                    <Image 
                      key={i} 
                      src={`https://i.pravatar.cc/100?u=${i+10}`} 
                      className="w-10 h-10 rounded-full border-2 border-white shadow-sm" 
                      alt="User avatar"
                      width={40}
                      height={40}
                    />
                  ))}
                </div>
                <p className="text-sm font-bold text-zinc-400 italic uppercase tracking-widest">
                  &quot;Now I sound like a CEO, not a student.&quot;
                </p>
              </div>
            </motion.div>

            {/* Persona 2: Consultant */}
            <motion.div 
               initial={{ opacity: 0, scale: 0.95 }}
               whileInView={{ opacity: 1, scale: 1 }}
               viewport={{ once: true }}
               className="md:col-span-6 lg:col-span-4 bg-zinc-50 border border-zinc-200 rounded-[2.5rem] p-6 sm:p-10 relative overflow-hidden group hover:bg-white hover:border-indigo-100 transition-all duration-500"
            >
              <div className="relative z-10">
                <div className="w-12 h-12 bg-white rounded-xl shadow-sm border border-zinc-200 flex items-center justify-center text-2xl mb-6">💼</div>
                <h4 className="text-2xl font-bold text-zinc-900 mb-3 tracking-tight">The Consultant</h4>
                <p className="text-zinc-600 leading-relaxed font-medium mb-6">
                  Protect your premium rates by staying visible. Ground your content in your real methodologies.
                </p>
                <div className="text-[#6E56CF] font-bold text-sm inline-flex items-center gap-2 px-3 py-1 bg-indigo-50 border border-indigo-100 rounded-lg">
                  100% On-Brand
                </div>
              </div>
            </motion.div>

            {/* Persona 3: HR/Recruiter */}
            <motion.div 
               initial={{ opacity: 0, y: 20 }}
               whileInView={{ opacity: 1, y: 0 }}
               viewport={{ once: true }}
               transition={{ delay: 0.1 }}
               className="md:col-span-3 lg:col-span-4 bg-zinc-50 border border-zinc-200 rounded-[2.5rem] p-8 relative overflow-hidden group hover:border-[#818CF8]/30 transition-all"
            >
              <div className="relative z-10">
                <div className="text-3xl mb-4">🎯</div>
                <h4 className="text-xl font-bold text-zinc-900 mb-2">The Expert Hire</h4>
                <p className="text-sm text-zinc-600 font-medium">Position yourself for that $250k+ role by building a documented track record of expertise.</p>
              </div>
            </motion.div>

            {/* Persona 4: Agency Owner */}
            <motion.div 
               initial={{ opacity: 0, y: 20 }}
               whileInView={{ opacity: 1, y: 0 }}
               viewport={{ once: true }}
               transition={{ delay: 0.2 }}
               className="md:col-span-3 lg:col-span-4 bg-indigo-50 border border-indigo-200 rounded-[2.5rem] p-8 relative overflow-hidden group hover:bg-white hover:border-indigo-100 transition-all duration-500"
            >
              <div className="relative z-10">
                <div className="text-3xl mb-4">🏢</div>
                <h4 className="text-xl font-bold text-zinc-900 mb-2">The Agency Owner</h4>
                <p className="text-sm text-zinc-600 font-medium">Scale content across 10 client profiles without increasing headcount or sacrificing quality.</p>
              </div>
              <div className="absolute bottom-0 right-0 w-24 h-24 bg-indigo-100/30 rounded-tl-3xl blur-[20px] pointer-events-none" />
            </motion.div>

            {/* Persona 5: High-Impact Individual */}
            <motion.div 
               initial={{ opacity: 0, y: 20 }}
               whileInView={{ opacity: 1, y: 0 }}
               viewport={{ once: true }}
               transition={{ delay: 0.3 }}
               className="md:col-span-6 lg:col-span-4 bg-zinc-50 border border-zinc-200 rounded-[2.5rem] p-8 relative overflow-hidden group"
            >
              <div className="relative z-10">
                <div className="text-3xl mb-4">🌟</div>
                <h4 className="text-xl font-bold text-zinc-900 mb-2">The Creator</h4>
                <p className="text-sm text-zinc-600 font-medium">Turn your research and long-form articles into a weeks&apos; worth of engaging LinkedIn carousels and posts.</p>
              </div>
            </motion.div>
          </div>
        </div>
      </section>

      {/* Why LinkedIn Matters Right Now */}
      <section className="py-24 md:py-32 bg-white text-zinc-900 relative overflow-hidden border-y border-zinc-100">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-indigo-50/50 rounded-full blur-[120px] pointer-events-none" />
        
        <div className="container mx-auto px-6 max-w-6xl relative z-10">
           <div className="text-center mb-20 max-w-3xl mx-auto">
             <h2 className="text-indigo-600 font-bold tracking-widest uppercase text-xs mb-3">The Landscape</h2>
             <h3 className="text-4xl md:text-5xl font-bold mb-6 text-zinc-900 tracking-tight">Consistency on LinkedIn is not optional. It compounds.</h3>
             <p className="text-xl text-zinc-600 leading-relaxed font-medium">
               The brutal truth: If you posted once last month, LinkedIn&apos;s algorithm has already classified your profile as inactive. Every week of silence is a week your competitors gain ground.
             </p>
           </div>
           
           <div className="grid md:grid-cols-2 gap-12 mb-20">
             <div className="flex gap-4">
               <div className="shrink-0 w-12 h-12 rounded-xl bg-indigo-50 border border-indigo-100 flex items-center justify-center text-xl shadow-sm">📱</div>
               <div>
                 <h4 className="text-xl font-bold text-zinc-900 mb-2">Live Sales Page</h4>
                 <p className="text-zinc-600 leading-relaxed font-medium">Decision-makers check your LinkedIn before every meeting. If your last post was 3 weeks ago, you signal doubt before the conversation starts.</p>
               </div>
             </div>
             <div className="flex gap-4">
               <div className="shrink-0 w-12 h-12 rounded-xl bg-indigo-50 border border-indigo-100 flex items-center justify-center text-xl shadow-sm">⚙️</div>
               <div>
                 <h4 className="text-xl font-bold text-zinc-900 mb-2">A System Problem</h4>
                  <p className="text-zinc-600 leading-relaxed font-medium">You don&apos;t miss posting because you&apos;re lazy. You miss it because the workflow breaks when life gets busy. Velank AI is the system that keeps running.</p>
               </div>
             </div>
             <div className="flex gap-4">
               <div className="shrink-0 w-12 h-12 rounded-xl bg-indigo-50 border border-indigo-100 flex items-center justify-center text-xl shadow-sm">📈</div>
               <div>
                 <h4 className="text-xl font-bold text-zinc-900 mb-2">Compounding Authority</h4>
                 <p className="text-zinc-600 leading-relaxed font-medium">Your 20th post reaches further than your 1st — because it rides on all the trust built before it. But only if you don&apos;t break the chain.</p>
               </div>
             </div>
             <div className="flex gap-4">
               <div className="shrink-0 w-12 h-12 rounded-xl bg-indigo-50 border border-indigo-100 flex items-center justify-center text-xl shadow-sm">🌐</div>
               <div>
                 <h4 className="text-xl font-bold text-zinc-900 mb-2">SEO Real Estate</h4>
                 <p className="text-zinc-600 leading-relaxed font-medium">Professionals who post consistently own search real estate in their niche — discoverable far beyond their immediate network.</p>
               </div>
             </div>
           </div>
           
           {/* Data Cards */}
           <div className="bg-indigo-50/50 border border-indigo-100 rounded-[2.5rem] p-8 md:p-12 shadow-sm">
              <h4 className="text-center font-bold text-indigo-600 uppercase tracking-widest text-[10px] mb-10">LinkedIn Platform Advantage</h4>
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-8 text-center">
                <div>
                  <div className="text-4xl font-black text-zinc-900 mb-2">1B+</div>
                  <div className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider">Members globally</div>
                </div>
                <div>
                  <div className="text-4xl font-black text-indigo-600 mb-2">4×</div>
                  <div className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider">Higher B2B Conv. Rate</div>
                </div>
                <div>
                  <div className="text-4xl font-black text-amber-500 mb-2">561%</div>
                  <div className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider">More Reach vs Companies</div>
                </div>
                <div>
                  <div className="text-4xl font-black text-emerald-600 mb-2">3%</div>
                  <div className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider">Create Content. They win.</div>
                </div>
              </div>
           </div>
        </div>
      </section>

      {/* ROI Transformation Section - The "Chaotic vs. Order" Metaphor */}
      <section className="py-32 bg-zinc-50 text-zinc-900 relative overflow-hidden">
        <div className="absolute inset-0 bg-[url('https://res.cloudinary.com/dzbcnwqut/image/upload/v1703649553/grid_q29nt2.svg')] opacity-[0.02] pointer-events-none" />
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full max-w-4xl h-96 bg-indigo-100/50 blur-[150px] pointer-events-none rounded-full" />
        
        <div className="container mx-auto px-6 max-w-7xl relative z-10">
          <div className="text-center mb-24">
            <h2 className="text-indigo-600 font-bold tracking-[0.3em] uppercase text-[10px] mb-4">Content ROI</h2>
            <h3 className="text-4xl md:text-7xl font-bold tracking-tighter mb-8 leading-[1.1] text-zinc-900">
              The cost of silence <br/> is <span className="italic text-zinc-300">visible.</span>
            </h3>
          </div>
          
          <div className="grid lg:grid-cols-2 gap-8 items-stretch max-w-6xl mx-auto mb-20">
            {/* The Old Way: Stressful & Chaotic */}
            <motion.div 
               initial={{ opacity: 0, x: -30 }}
               whileInView={{ opacity: 1, x: 0 }}
               viewport={{ once: true }}
               className="bg-white border border-red-100 rounded-[2.5rem] p-6 sm:p-10 relative shadow-sm"
            >
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-red-50 border border-red-100 text-[10px] font-bold tracking-widest uppercase text-red-500 mb-8">
                Legacy Workflow
              </div>
              <h4 className="text-3xl font-bold mb-8 tracking-tight text-zinc-900">The &quot;Old Way&quot; Stress</h4>
              <ul className="space-y-6 mb-12">
                {[
                  "Random posting leads to 'Dead Profile' status",
                  "Staring at a blank cursor for 90 minutes",
                  "Generic AI content kills your professional brand",
                  "Visibility drops 80% when life gets busy"
                ].map((item, i) => (
                  <li key={i} className="flex gap-4 items-start text-zinc-600 font-medium">
                    <span className="shrink-0 w-6 h-6 rounded-full bg-red-50 border border-red-100 flex items-center justify-center text-red-500 text-[10px]">✕</span>
                    {item}
                  </li>
                ))}
              </ul>
              <div className="p-6 bg-red-50/50 border border-red-100 rounded-2xl flex items-center justify-between">
                <span className="text-sm font-bold text-zinc-400 uppercase tracking-tight">Yearly Time Lost</span>
                <span className="text-2xl font-bold text-red-600">300+ Hours</span>
              </div>
            </motion.div>

            {/* The Velank Way: Automated Authority */}
            <motion.div 
               initial={{ opacity: 0, x: 30 }}
               whileInView={{ opacity: 1, x: 0 }}
               viewport={{ once: true }}
               className="bg-white border border-indigo-200 rounded-[2.5rem] p-6 sm:p-10 shadow-xl shadow-indigo-100/50 relative group overflow-hidden"
            >
              <div className="absolute inset-0 bg-indigo-50/10 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none" />
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-600 text-[10px] font-bold tracking-widest uppercase text-white mb-8">
                Velank AI Ecosystem
              </div>
              <h4 className="text-3xl font-bold mb-8 tracking-tight text-zinc-900">Compound Authority</h4>
              <ul className="space-y-6 mb-12">
                {[
                  "Automated consistency protects your network reach",
                  "5-minute drafts grounded in your unique facts",
                  "Recognizable expertise via Digital Twin voice",
                  "Inbound leads generated while you sleep"
                ].map((item, i) => (
                  <li key={i} className="flex gap-4 items-start text-zinc-600 font-bold">
                    <span className="shrink-0 w-6 h-6 rounded-full bg-indigo-600 flex items-center justify-center text-white text-[10px]">✓</span>
                    {item}
                  </li>
                ))}
              </ul>
              <div className="p-6 bg-indigo-50 border border-indigo-100 rounded-2xl flex items-center justify-between">
                <span className="text-sm font-bold text-indigo-600 uppercase tracking-widest">Growth Factor</span>
                <span className="text-2xl font-bold text-zinc-900">7x Visibility</span>
              </div>
            </motion.div>
          </div>

          {/* Sell with Real Data Insight */}
          <motion.div 
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="bg-white border border-zinc-200 rounded-[2.5rem] p-8 md:p-12 text-left relative overflow-hidden shadow-sm"
          >
             <div className="absolute top-0 right-0 w-64 h-64 bg-emerald-50 blur-[80px] pointer-events-none -translate-y-1/2 translate-x-1/2" />
             <div className="flex flex-col lg:flex-row items-center justify-between gap-12 relative z-10">
               <div className="lg:w-1/2">
                 <h4 className="text-3xl font-bold text-zinc-900 mb-4 tracking-tighter">Profit from Authority.</h4>
                 <p className="text-zinc-600 font-medium leading-relaxed mb-8">
                   Don&apos;t just post—convert. Actively posting on LinkedIn transforms your profile from a static resume into an automated outbound engine. 
                 </p>
                 <div className="grid grid-cols-2 gap-6">
                    <div className="p-4 bg-zinc-50 rounded-2xl border border-zinc-100">
                       <div className="text-2xl font-black text-emerald-600 mb-1">7×</div>
                       <div className="text-[10px] font-bold text-zinc-400 uppercase">Profile Views</div>
                    </div>
                    <div className="p-4 bg-zinc-50 rounded-2xl border border-zinc-100">
                       <div className="text-2xl font-black text-indigo-600 mb-1">2.4×</div>
                       <div className="text-[10px] font-bold text-zinc-400 uppercase">Inbound Leads</div>
                    </div>
                 </div>
               </div>
               
               <div className="lg:w-1/2 w-full bg-zinc-50 border border-zinc-100 rounded-3xl p-8 shadow-inner">
                 <div className="text-[10px] font-bold text-zinc-400 uppercase tracking-[0.2em] mb-8 border-b border-zinc-100 pb-4">Real-Time Performance Delta</div>
                 <div className="grid grid-cols-2 gap-8 mb-8">
                   <div>
                     <div className="text-sm text-zinc-400 mb-1">Global Engagement</div>
                     <div className="text-3xl font-bold text-zinc-900 tracking-tighter">142,402</div>
                     <div className="text-[11px] text-emerald-600 font-bold mt-1 flex items-center gap-1">
                        <TrendingUp className="w-3 h-3" /> +14.2%
                     </div>
                   </div>
                   <div>
                     <div className="text-sm text-zinc-400 mb-1">Direct ROI</div>
                     <div className="text-3xl font-bold text-zinc-900 tracking-tighter">$24.2k</div>
                     <div className="text-[11px] text-emerald-600 font-bold mt-1 flex items-center gap-1">
                        <TrendingUp className="w-3 h-3" /> Monthly Avg
                     </div>
                   </div>
                 </div>
                 <div className="space-y-4 pt-4 border-t border-zinc-100">
                    <div className="h-2 w-full bg-zinc-200/50 rounded-full overflow-hidden">
                       <motion.div 
                          initial={{ width: 0 }}
                          whileInView={{ width: "85%" }}
                          transition={{ duration: 1.5, ease: "easeOut" }}
                          className="h-full bg-indigo-500" 
                       />
                    </div>
                    <div className="flex justify-between text-[10px] font-bold text-zinc-400 uppercase tracking-widest">
                       <span>Market Reach</span>
                       <span className="text-zinc-900">85% Capacity</span>
                    </div>
                 </div>
               </div>
             </div>
          </motion.div>
        </div>
      </section>

      {/* Enterprise / Team Solutions */}
      <section className="py-24 md:py-32 bg-zinc-900 text-white relative overflow-hidden">
        <div className="absolute top-0 right-0 w-[600px] h-[600px] bg-indigo-500/10 rounded-full blur-[120px] pointer-events-none -translate-y-1/2 translate-x-1/2" />
        <div className="container mx-auto px-6 max-w-6xl relative z-10">
          <div className="flex flex-col lg:flex-row items-center gap-16">
            <div className="lg:w-1/2">
               <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/10 border border-white/20 text-[10px] font-bold tracking-widest uppercase text-indigo-300 mb-8">
                  Enterprise Ready
               </div>
               <h3 className="text-4xl md:text-5xl font-black mb-6 tracking-tight leading-tight">
                  Scaling content for <br/> <span className="text-indigo-400">entire B2B teams.</span>
               </h3>
               <p className="text-xl text-zinc-400 mb-10 leading-relaxed font-medium">
                  Agencies, sales organizations, and marketing departments use Velank AI to maintain a unified voice cross 100+ profiles without increasing headcount.
               </p>
               <div className="space-y-4">
                  {[
                    "Centralized workspace for multiple brands",
                    "Approval workflows for legal & compliance",
                    "Custom training for proprietary datasets",
                    "Dedicated account success manager"
                  ].map((feat, i) => (
                    <div key={i} className="flex gap-3 items-center text-zinc-300 font-bold">
                       <CheckCircle2 className="w-5 h-5 text-indigo-400" />
                       {feat}
                    </div>
                  ))}
               </div>
            </div>
            <div className="lg:w-1/2 w-full">
               <div className="bg-white/5 border border-white/10 rounded-[3rem] p-8 md:p-12 relative overflow-hidden backdrop-blur-sm shadow-2xl">
                  <div className="text-center">
                    <div className="text-zinc-400 font-bold uppercase tracking-widest text-[10px] mb-4">Enterprise Inquiries</div>
                    <p className="text-2xl font-bold mb-8">Need a custom solution for 10+ profiles?</p>
                    <Link href="https://app.velank.io/login" className="inline-flex items-center justify-center rounded-2xl font-black transition-all bg-white text-zinc-900 hover:bg-zinc-100 h-16 px-8 md:px-12 text-lg shadow-xl shadow-white/5">
                       Contact Sales <ArrowRight className="ml-2 w-5 h-5" />
                    </Link>
                    <p className="mt-6 text-xs text-zinc-500 font-medium italic">Dedicated support for teams spending $2k+/mo on content.</p>
                  </div>
               </div>
            </div>
          </div>
        </div>
      </section>

      {/* Comparison Section - High-End SaaS Table */}
      <section className="py-32 bg-white relative overflow-hidden">
        <div className="container mx-auto px-6 max-w-5xl relative z-10">
          <div className="text-center mb-20">
             <h2 className="text-4xl md:text-5xl font-bold text-zinc-900 tracking-tighter">Smart scale vs. <br/> <span className="text-zinc-400">Legacy methods</span></h2>
          </div>
          
          <div className="overflow-x-auto rounded-[2rem] border border-zinc-200">
            <table className="w-full text-left bg-white border-collapse">
              <thead>
                <tr className="border-b border-zinc-100">
                  <th className="p-8 text-xs font-bold text-zinc-400 uppercase tracking-widest">Feature Comparison</th>
                  <th className="p-8 text-sm font-black text-indigo-600 bg-indigo-50/30">✦ Velank AI</th>
                  <th className="p-8 text-xs font-bold text-zinc-400 uppercase tracking-widest">Agencies</th>
                  <th className="p-8 text-xs font-bold text-zinc-400 uppercase tracking-widest">Manual</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-50">
                {[
                  { label: "Content Strategy", fy: "AI-Driven Context", ag: "Human/Slow", ma: "None" },
                  { label: "Cost (Effort)", fy: "Negligible", ag: "$3k - $8k/mo", ma: "15hr+/week" },
                  { label: "Voice Consistency", fy: "Digital Twin Tech", ag: "Depends on writer", ma: "Hard to maintain" },
                  { label: "Turnaround", fy: "Instant", ag: "3-5 Business Days", ma: "Infinite" }
                ].map((row, i) => (
                  <tr key={i} className="hover:bg-zinc-50/50 transition-colors">
                    <td className="p-8 text-zinc-900 font-bold">{row.label}</td>
                    <td className="p-8 font-bold text-indigo-600 bg-indigo-50/10 border-x border-indigo-100/20">{row.fy}</td>
                    <td className="p-8 text-zinc-500 font-medium">{row.ag}</td>
                    <td className="p-8 text-zinc-500 font-medium">{row.ma}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* Final CTA Section - High Impact High Motion */}
      <section className="py-40 relative overflow-hidden bg-white">
        <div className="container mx-auto px-6 max-w-6xl relative z-10 text-center">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            whileInView={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.8 }}
            className="bg-zinc-50 border border-zinc-200 rounded-[3rem] p-16 md:p-32 relative overflow-hidden text-center shadow-2xl"
          >
            {/* Animated background decoration */}
            <div className="absolute inset-0 bg-gradient-to-br from-indigo-50 via-transparent to-emerald-50 pointer-events-none opacity-40" />
            <div className="absolute top-0 left-0 w-full h-full bg-[url('https://res.cloudinary.com/dzbcnwqut/image/upload/v1703649553/grid_q29nt2.svg')] opacity-[0.03] pointer-events-none" />
            
            <motion.div
              animate={{ 
                rotate: [0, 5, 0, -5, 0],
                y: [0, -10, 5, -5, 0]
              }}
              transition={{ duration: 15, repeat: Infinity, ease: "easeInOut" }}
              className="absolute top-1/4 right-10 w-64 h-64 bg-indigo-100 rounded-full blur-[80px] pointer-events-none"
            />

            <div className="relative z-10">
              <h2 className="text-4xl md:text-7xl font-extrabold tracking-tighter mb-8 text-zinc-900 leading-[1.05]">
                Your competitors are <br/> posting <span className="text-indigo-600 italic">right now.</span>
              </h2>
              <p className="text-xl text-zinc-600 mb-12 max-w-2xl mx-auto font-medium leading-relaxed">
                They didn&apos;t find &quot;more time.&quot; They found a smarter engine. Join 20,000+ elite professionals scaling their reach on autopilot.
              </p>
              
              <div className="flex flex-col items-center gap-10">
                <MagneticButton>
                  <Link href="https://app.velank.io/login" className="inline-flex items-center justify-center rounded-2xl font-black transition-all bg-indigo-600 text-white hover:bg-indigo-700 h-16 md:h-20 px-8 md:px-16 text-lg md:text-2xl shadow-xl shadow-indigo-200 transform active:scale-95 group">
                    Scale Your Presence <ArrowRight className="ml-3 w-5 h-5 md:w-6 md:h-6 group-hover:translate-x-2 transition-transform" />
                  </Link>
                </MagneticButton>
                
                <div className="flex flex-wrap items-center justify-center gap-8 md:gap-12 pt-12 border-t border-zinc-200 w-full max-w-2xl">
                   <div className="flex items-center gap-2 text-zinc-500 font-bold text-xs uppercase tracking-widest">
                      <CheckCircle2 className="w-4 h-4 text-emerald-500" /> 30% Discount
                   </div>
                   <div className="flex items-center gap-2 text-zinc-500 font-bold text-xs uppercase tracking-widest">
                      <CheckCircle2 className="w-4 h-4 text-emerald-500" /> No Card Required
                   </div>
                   <div className="flex items-center gap-2 text-zinc-500 font-bold text-xs uppercase tracking-widest">
                      <CheckCircle2 className="w-4 h-4 text-emerald-500" /> Cancel Anytime
                   </div>
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      <Footer />
    </div>
  );
}
