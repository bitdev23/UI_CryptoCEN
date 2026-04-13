"use client";

import { motion } from "framer-motion";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { InteractiveGrid } from "@/components/ui/InteractiveGrid";
import { MagneticButton } from "@/components/ui/MagneticButton";
import Link from "next/link";
import { 
  Sparkles, 
  ArrowRight, 
  ShieldCheck, 
  Check, 
  X, 
  AlertTriangle, 
  Zap, 
  Brain, 
  DollarSign,
  Award
} from "lucide-react";

const COMPARISON_FEATURES = [
  { 
    feature: "Generates from your own documents", 
    taplio: false, 
    velank: true,
    detail: "Velank reads your real expertise (decks, docs, case studies). Taplio doesn&apos;t." 
  },
  { 
    feature: "Hallucination guardrails", 
    taplio: false, 
    velank: true,
    detail: "Velank prevents AI from inventing fake facts or stats." 
  },
  { 
    feature: "Role & industry context", 
    taplio: "Limited", 
    velank: "Full Control",
    detail: "Velank sets your professional identity once and sticks to it." 
  },
  { 
    feature: "AI post generation", 
    taplio: "250 credits/mo cap", 
    velank: "Unlimited",
    detail: "Taplio&apos;s Standard plan limits how much you can create." 
  },
  { 
    feature: "LinkedIn API Method", 
    taplio: "Cookie-based (Risky)", 
    velank: "Official OAuth API",
    detail: "Velank uses official methods to keep your account safe from bans." 
  },
  { 
    feature: "Starts with real AI for free", 
    taplio: false, 
    velank: true,
    detail: "Velank gives you 3 grounded drafts forever for $0. No card needed." 
  },
];

export default function TaplioComparison() {
  return (
    <div className="min-h-screen bg-zinc-50 text-zinc-900 relative flex flex-col pt-28 font-sans overflow-hidden">
      <Header />
      
      {/* 1. Hero Section */}
      <section className="pt-24 pb-32 relative border-b border-zinc-200 overflow-hidden bg-white">
        <InteractiveGrid />
        <div className="absolute top-0 right-0 w-[600px] h-[600px] bg-indigo-50/50 rounded-full blur-[120px] pointer-events-none -translate-y-1/2 translate-x-1/3 opacity-50" />
        
        <div className="container mx-auto px-6 relative z-10 max-w-6xl text-center">
          <nav className="flex items-center justify-center gap-2 text-xs font-bold uppercase tracking-widest text-zinc-400 mb-12">
            <Link href="/" className="hover:text-indigo-600 transition-colors">Home</Link>
            <span>/</span>
            <span className="text-zinc-500">Compare</span>
            <span>/</span>
            <span className="text-indigo-600">Velank vs Taplio</span>
          </nav>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7 }}
          >
            <div className="flex items-center justify-center gap-4 md:gap-8 mb-8">
              <div className="bg-white border-2 border-indigo-600 p-4 rounded-3xl shadow-xl shadow-indigo-100 h-20 w-20 md:h-24 md:w-24 flex items-center justify-center">
                <span className="text-2xl md:text-3xl font-black text-indigo-600 italic tracking-tighter">V</span>
              </div>
              <div className="text-zinc-300 text-3xl md:text-5xl font-light italic">vs</div>
              <div className="bg-white border border-zinc-200 p-4 rounded-3xl shadow-sm h-20 w-20 md:h-24 md:w-24 flex items-center justify-center">
                <span className="text-2xl md:text-3xl font-bold text-zinc-400">T</span>
              </div>
            </div>

            <h1 className="text-4xl md:text-7xl font-black tracking-tight mb-8 text-zinc-900 leading-[1.1] px-2">
              Taplio charges $65/mo <br className="hidden md:block" />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-red-500 to-indigo-600">
                before you get any AI at all.
              </span>
            </h1>
            
            <p className="text-xl md:text-2xl text-zinc-600 mb-12 max-w-4xl mx-auto font-medium leading-relaxed">
              Taplio&apos;s $39 Starter plan has zero AI features. You need Standard at $65/mo minimum to do what Velank does at $29/mo — with hallucination guardrails and knowledge base generation that Taplio doesn&apos;t offer at any price.
            </p>
            
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <MagneticButton>
                <Link href="https://app.velank.io/login" className="inline-flex items-center justify-center rounded-2xl font-black transition-all bg-indigo-600 text-white hover:bg-indigo-700 h-16 md:h-20 px-8 md:px-12 text-lg md:text-xl shadow-xl shadow-indigo-200 group">
                  Try Velank Free — No Card Needed <ArrowRight className="ml-3 w-5 h-5 group-hover:translate-x-1 transition-transform" />
                </Link>
              </MagneticButton>
              <button 
                onClick={() => document.getElementById('feature-table')?.scrollIntoView({ behavior: 'smooth' })}
                className="text-zinc-500 font-bold hover:text-zinc-900 transition-colors flex items-center gap-2"
              >
                See full comparison <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </motion.div>
        </div>
      </section>

      {/* 2. Key Highlights */}
      <section className="py-24 bg-zinc-50">
        <div className="container mx-auto px-6 max-w-7xl">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="bg-white p-8 rounded-[2rem] border border-zinc-200 shadow-sm hover:shadow-lg transition-all duration-300">
              <div className="w-12 h-12 bg-indigo-50 rounded-2xl flex items-center justify-center mb-6">
                <Brain className="w-6 h-6 text-indigo-600" />
              </div>
              <h4 className="text-xl font-bold mb-3">Knowledge base engine</h4>
              <p className="text-zinc-600 font-medium">Velank only — not available in Taplio. Ground your posts in real expertise, not generic prompts.</p>
            </div>
            <div className="bg-white p-8 rounded-[2rem] border border-zinc-200 shadow-sm hover:shadow-lg transition-all duration-300">
              <div className="w-12 h-12 bg-emerald-50 rounded-2xl flex items-center justify-center mb-6">
                <ShieldCheck className="w-6 h-6 text-emerald-600" />
              </div>
              <h4 className="text-xl font-bold mb-3">Hallucination guardrails</h4>
              <p className="text-zinc-600 font-medium">Velank ensures your reputation is safe. Taplio often invents facts when it runs out of context.</p>
            </div>
            <div className="bg-white p-8 rounded-[2rem] border border-zinc-200 shadow-sm hover:shadow-lg transition-all duration-300 border-b-4 border-b-indigo-500">
              <div className="w-12 h-12 bg-indigo-50 rounded-2xl flex items-center justify-center mb-6">
                <DollarSign className="w-6 h-6 text-indigo-600" />
              </div>
              <h4 className="text-xl font-bold mb-3">$29/mo vs $65/mo</h4>
              <p className="text-zinc-600 font-medium">For equivalent AI features. Stop paying the &quot;convenience tax&quot; for a tool built on aging tech.</p>
            </div>
          </div>
        </div>
      </section>

      {/* 3. Verdict Cards */}
      <section className="py-32 bg-white relative">
        <div className="container mx-auto px-6 max-w-6xl">
          <div className="text-center mb-16">
            <h2 className="text-[10px] uppercase font-bold tracking-[0.3em] text-zinc-400 mb-4">Quick Verdict</h2>
            <h3 className="text-3xl md:text-5xl font-black text-zinc-900 tracking-tight">Bottom line before you read anything else.</h3>
          </div>

          <div className="grid md:grid-cols-2 gap-8 items-stretch">
            {/* Velank Verdict */}
            <motion.div 
              initial={{ opacity: 0, x: -20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              className="bg-zinc-900 rounded-[3rem] p-6 sm:p-10 md:p-12 text-white relative overflow-hidden border-2 border-indigo-500 shadow-2xl"
            >
              <div className="absolute top-0 right-0 w-32 h-32 bg-indigo-500/20 rounded-full blur-2xl" />
              <div className="flex justify-between items-start mb-10">
                <div>
                  <h4 className="text-xl font-bold text-indigo-400 mb-1">For knowledge-based authority</h4>
                  <div className="text-4xl font-black">Velank AI</div>
                </div>
                <div className="text-5xl font-black text-indigo-500">9.1</div>
              </div>
              <p className="text-zinc-400 text-lg mb-8 leading-relaxed">
                Best for: founders, consultants, B2B pros who want posts grounded in their actual expertise.
              </p>
              <div className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 rounded-full text-xs font-black uppercase tracking-widest shadow-lg">
                <Sparkles className="w-3.5 h-3.5" /> Recommended
              </div>
              <div className="mt-12 space-y-4 pt-10 border-t border-white/10">
                <div className="flex gap-3 text-emerald-400 font-bold">
                  <Check className="w-5 h-5 shrink-0" />
                  <span>Content that actually sounds like you</span>
                </div>
                <div className="flex gap-3 text-emerald-400 font-bold">
                  <Check className="w-5 h-5 shrink-0" />
                  <span>Safe, official LinkedIn API only</span>
                </div>
              </div>
            </motion.div>

            {/* Taplio Verdict */}
            <motion.div 
              initial={{ opacity: 0, x: 20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              className="bg-white border-2 border-zinc-100 rounded-[3rem] p-6 sm:p-10 md:p-12 text-zinc-900 relative overflow-hidden shadow-sm hover:shadow-xl transition-all"
            >
              <div className="flex justify-between items-start mb-10">
                <div>
                  <h4 className="text-xl font-bold text-zinc-400 mb-1">For outreach + lead gen</h4>
                  <div className="text-4xl font-black">Taplio</div>
                </div>
                <div className="text-5xl font-black text-zinc-300">6.4</div>
              </div>
              <p className="text-zinc-500 text-lg mb-8 leading-relaxed">
                If you primarily need LinkedIn outreach automation + a lead database, Taplio Pro is worth considering. For content — Velank wins.
              </p>
              <div className="text-zinc-400 font-medium italic">
                Best for: sales teams who need lead databases as their primary goal.
              </div>
               <div className="mt-12 space-y-4 pt-10 border-t border-zinc-100">
                <div className="flex gap-3 text-zinc-400 font-medium">
                  <X className="w-5 h-5 shrink-0 text-red-400" />
                  <span>Bait-and-switch pricing structure</span>
                </div>
                <div className="flex gap-3 text-zinc-400 font-medium">
                  <X className="w-5 h-5 shrink-0 text-red-400" />
                  <span>AI content requires Standard plan ($65/mo)</span>
                </div>
              </div>
            </motion.div>
          </div>
        </div>
      </section>

      {/* 4. Pricing Reality Check */}
      <section className="py-32 bg-zinc-50 relative overflow-hidden">
        <div className="container mx-auto px-6 max-w-6xl">
          <div className="text-center mb-24">
            <h2 className="text-indigo-600 font-bold tracking-[0.3em] uppercase text-[10px] mb-4">Pricing Reality Check</h2>
            <h3 className="text-4xl md:text-6xl font-black text-zinc-900 tracking-tight leading-tight">
              Taplio&apos;s real cost is <br className="hidden md:block"/> <span className="text-red-600">not what it advertises.</span>
            </h3>
            <p className="text-xl text-zinc-600 mt-8 font-medium max-w-2xl mx-auto">
              The $39/mo Starter plan has no AI content generation. You need Standard ($65/mo) just to get the features Velank includes at $29/mo.
            </p>
          </div>

          <div className="grid lg:grid-cols-2 gap-12">
            {/* Taplio Reality */}
            <div className="space-y-4">
              <h4 className="text-2xl font-black mb-8 flex items-center gap-3">
                Taplio <span className="text-zinc-400 italic">&quot;What you pay&quot;</span>
              </h4>
              <div className="p-8 bg-white border border-red-100 rounded-3xl relative shadow-sm">
                <div className="flex justify-between items-center mb-2">
                  <span className="font-bold text-zinc-900">Starter</span>
                  <span className="text-xl font-black text-zinc-900">$39/mo</span>
                </div>
                <p className="text-sm text-red-500 font-bold flex items-center gap-2 mb-4">
                  <AlertTriangle className="w-4 h-4" /> ⚠️ Zero AI content generation
                </p>
                <div className="h-1 w-full bg-zinc-100 rounded-full" />
              </div>
              
              <div className="p-8 bg-zinc-900 text-white rounded-3xl relative shadow-2xl border-2 border-red-600">
                <div className="absolute top-0 right-10 -translate-y-1/2 bg-red-600 text-white text-[10px] font-black px-4 py-1 rounded-full uppercase tracking-widest">Minimum for AI</div>
                <div className="flex justify-between items-center mb-2">
                  <span className="font-bold">Standard</span>
                  <span className="text-2xl font-black">$65/mo</span>
                </div>
                <p className="text-zinc-400 text-sm mb-4">250 AI credits only · runs out fast if you&apos;re active.</p>
                <div className="h-1 w-full bg-white/10 rounded-full overflow-hidden">
                  <div className="h-full bg-red-600 w-full" />
                </div>
              </div>
              
              <div className="p-8 bg-white border border-zinc-200 rounded-3xl shadow-sm">
                <div className="flex justify-between items-center mb-2">
                  <span className="font-bold text-zinc-900">Pro</span>
                  <span className="text-xl font-black text-zinc-400">$199/mo</span>
                </div>
                <p className="text-sm text-zinc-500 font-medium">Lead database + auto-DM features.</p>
              </div>
              
              <div className="p-6 bg-red-50 rounded-2xl border border-red-100 mt-8">
                <p className="text-sm text-red-600 font-bold leading-relaxed">
                  ⚠️ Most users start at $39, discover it has no AI, and are forced up to $65. That&apos;s a bait-and-switch pricing structure.
                </p>
              </div>
            </div>

            {/* Velank Reality */}
            <div className="space-y-4">
              <h4 className="text-2xl font-black mb-8 flex items-center gap-3">
                Velank AI <span className="text-indigo-600 italic">&quot;No surprises&quot;</span>
              </h4>
              <div className="p-8 bg-white border border-zinc-200 rounded-3xl shadow-sm">
                <div className="flex justify-between items-center mb-2">
                  <span className="font-bold text-zinc-900">Free Forever</span>
                  <span className="text-xl font-black text-emerald-600">$0</span>
                </div>
                <p className="text-sm text-zinc-500 font-medium">3 full AI drafts from your docs · no card ever.</p>
              </div>
              
              <div className="p-8 bg-white text-zinc-900 rounded-3xl relative shadow-2xl border-2 border-indigo-600">
                <div className="absolute top-0 right-10 -translate-y-1/2 bg-indigo-600 text-white text-[10px] font-black px-4 py-1 rounded-full uppercase tracking-widest">Best Choice</div>
                <div className="flex justify-between items-center mb-2">
                  <span className="font-bold text-xl">Pro (Monthly)</span>
                  <span className="text-2xl font-black text-indigo-600">$29/mo</span>
                </div>
                <p className="text-zinc-500 text-sm mb-4">Unlimited posts · full knowledge base · scheduling included.</p>
                <div className="h-1 w-full bg-indigo-100 rounded-full overflow-hidden">
                  <div className="h-full bg-indigo-600 w-full" />
                </div>
              </div>
              
              <div className="p-8 bg-indigo-600 text-white rounded-3xl shadow-xl">
                <div className="flex justify-between items-center mb-2">
                  <span className="font-bold text-xl">Annual Plan</span>
                  <span className="text-2xl font-black">$199/yr</span>
                </div>
                <p className="text-indigo-100 text-sm font-medium italic">Unlimited everything · equivalent to $17/mo.</p>
              </div>
              
              <div className="p-6 bg-indigo-50 rounded-2xl border border-indigo-100 mt-8">
                <p className="text-sm text-indigo-600 font-bold leading-relaxed">
                  ✓ Velank Pro at $29/mo gives you more than Taplio Standard at $65/mo — at less than half the price.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 5. Feature Comparison Table */}
      <section id="feature-table" className="py-32 bg-white relative">
        <div className="container mx-auto px-6 max-w-5xl">
          <div className="text-center mb-20">
            <h2 className="text-4xl md:text-5xl font-black text-zinc-900 tracking-tighter">Feature by feature.</h2>
            <p className="text-xl text-zinc-500 mt-4 font-medium">What you actually get with each tool.</p>
          </div>

          <div className="overflow-x-auto rounded-[2.5rem] border border-zinc-200">
            <table className="w-full text-left bg-white border-collapse min-w-[700px]">
              <thead>
                <tr className="border-b border-zinc-100">
                  <th className="p-8 text-xs font-bold text-zinc-400 uppercase tracking-widest">Comparison</th>
                  <th className="p-8 text-sm font-bold text-zinc-400 uppercase tracking-widest">Taplio Standard</th>
                  <th className="p-8 text-sm font-black text-indigo-600 bg-indigo-50/30">✦ Velank AI Pro</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-50">
                {COMPARISON_FEATURES.map((item, i) => (
                  <tr key={i} className="hover:bg-zinc-50/50 transition-colors group">
                    <td className="p-8 align-top">
                      <div className="text-zinc-900 font-bold mb-1">{item.feature}</div>
                      <div className="text-xs text-zinc-400 font-medium opacity-0 group-hover:opacity-100 transition-opacity">{item.detail}</div>
                    </td>
                    <td className="p-8 align-top">
                      {item.taplio === true ? (
                        <div className="flex items-center gap-2 text-zinc-900 font-semibold"><Check className="w-5 h-5 text-zinc-300" /> Yes</div>
                      ) : item.taplio === false ? (
                        <div className="flex items-center gap-2 text-zinc-300"><X className="w-5 h-5 text-red-200" /> No</div>
                      ) : (
                        <div className="font-bold text-zinc-500 italic">{item.taplio}</div>
                      )}
                    </td>
                    <td className="p-8 align-top bg-indigo-50/10 border-x border-indigo-100/20">
                      {item.velank === true ? (
                        <div className="flex items-center gap-2 text-indigo-600 font-black"><Check className="w-6 h-6" /> Yes</div>
                      ) : (
                        <div className="font-black text-indigo-600">{item.velank}</div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          
          <div className="mt-12 p-8 bg-zinc-50 rounded-3xl border border-zinc-200 text-center">
             <div className="flex items-center justify-center gap-12 flex-wrap">
                <div>
                  <div className="text-zinc-400 text-xs font-bold uppercase tracking-widest mb-1">AI Cost / Mo</div>
                  <div className="text-3xl font-black text-zinc-300">$65.00</div>
                </div>
                <div className="text-zinc-200 text-4xl font-light">→</div>
                <div>
                  <div className="text-indigo-600 text-xs font-bold uppercase tracking-widest mb-1">Our Pro Plan</div>
                  <div className="text-4xl font-black text-indigo-600">$29.00</div>
                </div>
             </div>
          </div>
        </div>
      </section>

      {/* 6. Deep Dive Reasons */}
      <section className="py-32 bg-zinc-900 text-white relative overflow-hidden">
        <div className="absolute inset-0 bg-brand-mesh opacity-10 pointer-events-none" />
        <div className="container mx-auto px-6 max-w-6xl relative z-10">
          <div className="mb-24">
             <h2 className="text-4xl md:text-6xl font-black tracking-tight mb-4">Why people switch.</h2>
             <p className="text-xl text-zinc-400 max-w-2xl font-medium">The 4 reasons Taplio users move to Velank.</p>
          </div>

          <div className="grid md:grid-cols-2 gap-12">
            <div className="space-y-12">
              <div className="group">
                <div className="text-indigo-500 font-black text-6xl mb-6 opacity-20 group-hover:opacity-100 transition-opacity">01</div>
                <h4 className="text-2xl font-bold mb-4">The $39 plan is a trap</h4>
                <p className="text-zinc-400 leading-relaxed font-medium">
                  Users sign up for Taplio at $39/mo, then discover on day one that AI content generation requires the $65/mo Standard plan. It&apos;s a bait-and-switch that leaves a bad taste. Velank&apos;s free tier includes real AI output from your documents — no card required.
                </p>
              </div>
              <div className="group">
                <div className="text-indigo-500 font-black text-6xl mb-6 opacity-20 group-hover:opacity-100 transition-opacity">02</div>
                <h4 className="text-2xl font-bold mb-4">Taplio&apos;s AI still sounds like template output</h4>
                <p className="text-zinc-400 leading-relaxed font-medium">
                  Taplio generates from a blank prompt or generic topic. It has no access to your real expertise. The output requires heavy editing. Velank reads your actual documents — your case studies, decks, frameworks — and writes from there.
                </p>
              </div>
            </div>
            <div className="space-y-12 md:pt-24">
              <div className="group">
                <div className="text-indigo-500 font-black text-6xl mb-6 opacity-20 group-hover:opacity-100 transition-opacity">03</div>
                <h4 className="text-2xl font-bold mb-4">Account safety is a priority</h4>
                <p className="text-zinc-400 leading-relaxed font-medium">
                  LinkedIn temporarily blocked Taplio in 2024 because it relies on cookie-based scraping rather than the official API. Multiple users reported account restrictions. Velank uses only the official LinkedIn OAuth API — the method LinkedIn recommends.
                </p>
              </div>
              <div className="group">
                <div className="text-indigo-500 font-black text-6xl mb-6 opacity-20 group-hover:opacity-100 transition-opacity">04</div>
                <h4 className="text-2xl font-bold mb-4">Credit limits create anxiety</h4>
                <p className="text-zinc-400 leading-relaxed font-medium">
                  Taplio&apos;s Standard plan gives you 250 AI credits per month. Basic tasks burn through them fast. You end up rationing your own tool. Velank Pro is unlimited — generate as many posts as you need without watching a counter.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 7. Testimonials */}
      <section className="py-32 bg-white relative">
        <div className="container mx-auto px-6 max-w-6xl">
           <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
             <div className="bg-zinc-50 p-8 rounded-[2.5rem] border border-zinc-100 flex flex-col justify-between">
                <div>
                  <div className="flex text-amber-500 gap-1 mb-6">
                    {[1,2,3,4,5].map(i => <Sparkles key={i} className="w-4 h-4 fill-current" />)}
                  </div>
                  <p className="text-zinc-700 font-medium leading-relaxed italic mb-8">
                    &quot;I was paying $65/mo for Taplio Standard and still spending hours editing every post. Velank reads my actual proposals and case studies — the drafts need almost no editing because they&apos;re grounded in my expertise.&quot;
                  </p>
                </div>
                <div className="flex items-center gap-4 border-t border-zinc-200 pt-6">
                  <div className="w-10 h-10 rounded-full bg-indigo-600 flex items-center justify-center text-white font-black text-xs">NK</div>
                  <div>
                    <div className="text-sm font-black">Nisha K.</div>
                    <div className="text-[10px] uppercase font-bold text-zinc-400">Consultant · Pune</div>
                  </div>
                </div>
             </div>

             <div className="bg-indigo-50/50 p-8 rounded-[2.5rem] border border-indigo-100/50 flex flex-col justify-between scale-105 shadow-xl shadow-indigo-100/20 relative z-10">
                <div>
                  <div className="flex text-indigo-500 gap-1 mb-6">
                    {[1,2,3,4,5].map(i => <Award key={i} className="w-4 h-4 fill-current" />)}
                  </div>
                  <p className="text-zinc-800 font-bold leading-relaxed mb-8">
                    &quot;Taplio hit $65/mo before I got any AI worth using. I moved to Velank Pro at $29/mo and the output is better — because it comes from my documents, not generic prompts. The knowledge base feature alone is worth it.&quot;
                  </p>
                </div>
                <div className="flex items-center gap-4 border-t border-indigo-100 pt-6">
                  <div className="w-10 h-10 rounded-full bg-indigo-600 flex items-center justify-center text-white font-black text-xs">RM</div>
                  <div>
                    <div className="text-sm font-black">Rahul M.</div>
                    <div className="text-[10px] uppercase font-bold text-indigo-400">Founder · Bengaluru</div>
                  </div>
                </div>
             </div>

             <div className="bg-zinc-50 p-8 rounded-[2.5rem] border border-zinc-100 flex flex-col justify-between">
                <div>
                  <div className="flex text-amber-500 gap-1 mb-6">
                    {[1,2,3,4,5].map(i => <Zap key={i} className="w-4 h-4 fill-current" />)}
                  </div>
                  <p className="text-zinc-700 font-medium leading-relaxed italic mb-8">
                    &quot;After LinkedIn flagged my account once using cookie-based tools, I was done. Velank uses the official API and I haven&apos;t had a single issue. I sleep better and the content is better. Easy decision.&quot;
                  </p>
                </div>
                <div className="flex items-center gap-4 border-t border-zinc-200 pt-6">
                  <div className="w-10 h-10 rounded-full bg-zinc-900 flex items-center justify-center text-white font-black text-xs">JL</div>
                  <div>
                    <div className="text-sm font-black">James L.</div>
                    <div className="text-[10px] uppercase font-bold text-zinc-400">Growth Lead · London</div>
                  </div>
                </div>
             </div>
           </div>
        </div>
      </section>

      {/* 8. Final CTA */}
      <section className="py-40 bg-white">
        <div className="container mx-auto px-6 max-w-5xl text-center">
           <div className="bg-zinc-900 rounded-[3rem] p-16 md:p-24 relative overflow-hidden">
             <div className="absolute inset-0 bg-indigo-600/10 pointer-events-none" />
             <div className="relative z-10">
               <h2 className="text-4xl md:text-6xl font-black text-white mb-8 tracking-tight">
                 See the difference <br className="hidden md:block"/> in 10 minutes.
               </h2>
               <p className="text-xl text-zinc-400 mb-12 max-w-2xl mx-auto font-medium leading-relaxed">
                 Upload one document. Generate your first post. No credit card, no setup, no prompt engineering.
               </p>
               
               <div className="flex flex-col items-center gap-6">
                 <MagneticButton>
                   <Link href="https://app.velank.io/login" className="inline-flex items-center justify-center rounded-2xl font-black transition-all bg-indigo-600 text-white hover:bg-indigo-700 h-16 md:h-20 px-8 md:px-12 text-lg md:text-xl shadow-xl shadow-indigo-200 group">
                     Start Free — Try Velank Now <ArrowRight className="ml-3 w-5 h-5 group-hover:translate-x-1 transition-transform" />
                   </Link>
                 </MagneticButton>
                 <Link href="/pricing" className="text-zinc-500 hover:text-white transition-colors font-bold text-lg">See Pricing →</Link>
                 <p className="text-xs font-bold text-zinc-600 uppercase tracking-widest mt-4">
                   Free forever plan · Pro at $29/mo · Cancel anytime
                 </p>
               </div>
             </div>
           </div>
        </div>
      </section>

      <Footer />
    </div>
  );
}
