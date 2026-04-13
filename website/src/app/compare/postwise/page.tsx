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
  Zap, 
  Brain, 
  Target,
  BarChart3,
  Award,
  Twitter
} from "lucide-react";

const COMPARISON_FEATURES = [
  { 
    feature: "Generates from your own documents", 
    postwise: false, 
    velank: true,
    detail: "Postwise only uses generic prompts. Velank uses your documents (case studies, PDFs, decks)." 
  },
  { 
    feature: "Hallucination guardrails", 
    postwise: false, 
    velank: true,
    detail: "Velank prevents AI from inventing fake facts. Postwise has no verification." 
  },
  { 
    feature: "LinkedIn Post Analytics", 
    postwise: false, 
    velank: true,
    detail: "Velank tracks profile views and inbound. Postwise focuses on Twitter metrics." 
  },
  { 
    feature: "Iterative AI Refinement", 
    postwise: false, 
    velank: true,
    detail: "Velank lets you ask for hooks or tone shifts. Postwise requires manual editing." 
  },
  { 
    feature: "Algorithm Optimization", 
    postwise: "Twitter-First", 
    velank: "LinkedIn-First",
    detail: "Velank is specifically designed for LinkedIn's professional feed, not short-form X." 
  },
  { 
    feature: "Free tier with real AI output", 
    postwise: false, 
    velank: true,
    detail: "Velank gives you 3 grounded drafts forever for $0. No card needed." 
  },
];

export default function PostwiseComparison() {
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
            <span className="text-indigo-600">Velank vs Postwise</span>
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
                <Twitter className="w-10 h-10 text-sky-500" />
              </div>
            </div>

            <h1 className="text-4xl md:text-7xl font-black tracking-tight mb-8 text-zinc-900 leading-[1.1] px-2">
              Postwise was built for Twitter. <br className="hidden md:block" />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-sky-400 to-indigo-600">
                LinkedIn is not a side-hustle.
              </span>
            </h1>
            
            <p className="text-xl md:text-2xl text-zinc-600 mb-12 max-w-4xl mx-auto font-medium leading-relaxed">
              Postwise started as a Twitter tool and added LinkedIn as an afterthought. It has no knowledge base, no hallucination guardrails, and no way to generate content from your actual expertise.
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
                <Target className="w-6 h-6 text-indigo-600" />
              </div>
              <h4 className="text-xl font-bold mb-3">LinkedIn-first by design</h4>
              <p className="text-zinc-600 font-medium">Postwise is a Twitter tool with LinkedIn added on. Velank is optimized for professional algorithms from Day 0.</p>
            </div>
            <div className="bg-white p-8 rounded-[2rem] border border-zinc-200 shadow-sm hover:shadow-lg transition-all duration-300">
              <div className="w-12 h-12 bg-emerald-50 rounded-2xl flex items-center justify-center mb-6">
                <Brain className="w-6 h-6 text-emerald-600" />
              </div>
              <h4 className="text-xl font-bold mb-3">Real Knowledge Bases</h4>
              <p className="text-zinc-600 font-medium">Velank only — Postwise generates from prompts. We write from your actual documents, decks, and data.</p>
            </div>
            <div className="bg-white p-8 rounded-[2rem] border border-zinc-200 shadow-sm hover:shadow-lg transition-all duration-300 border-b-4 border-b-amber-500">
              <div className="w-12 h-12 bg-amber-50 rounded-2xl flex items-center justify-center mb-6">
                <BarChart3 className="w-6 h-6 text-amber-600" />
              </div>
              <h4 className="text-xl font-bold mb-3">Post-Level ROI Analytics</h4>
              <p className="text-zinc-600 font-medium">Postwise tracks Twitter likes. Velank tracks profile views and inbound performance on LinkedIn.</p>
            </div>
          </div>
        </div>
      </section>

      {/* 3. Verdict Cards */}
      <section className="py-32 bg-white relative">
        <div className="container mx-auto px-6 max-w-6xl">
          <div className="text-center mb-16">
            <h2 className="text-[10px] uppercase font-bold tracking-[0.3em] text-zinc-400 mb-4">Quick Verdict</h2>
            <h3 className="text-3xl md:text-5xl font-black text-zinc-900 tracking-tight">The honest bottom line.</h3>
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
                  <h4 className="text-xl font-bold text-indigo-400 mb-1">For LinkedIn authority</h4>
                  <div className="text-4xl font-black">Velank AI</div>
                </div>
                <div className="text-5xl font-black text-indigo-500">9.1</div>
              </div>
              <p className="text-zinc-400 text-lg mb-8 leading-relaxed font-medium">
                Best for: founders, consultants, and B2B pros who want grounded content that drives real pipeline.
              </p>
              <div className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 rounded-full text-xs font-black uppercase tracking-widest shadow-lg">
                <Sparkles className="w-3.5 h-3.5" /> Recommended
              </div>
              <div className="mt-12 space-y-4 pt-10 border-t border-white/10">
                <div className="flex gap-3 text-emerald-400 font-bold">
                  <Check className="w-5 h-5 shrink-0" />
                  <span>Grounds content in your real case studies</span>
                </div>
                <div className="flex gap-3 text-emerald-400 font-bold">
                  <Check className="w-5 h-5 shrink-0" />
                  <span>LinkedIn analytics that actually matter</span>
                </div>
              </div>
            </motion.div>

            {/* Postwise Verdict */}
            <motion.div 
              initial={{ opacity: 0, x: 20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              className="bg-white border-2 border-zinc-100 rounded-[3rem] p-6 sm:p-10 md:p-12 text-zinc-900 relative shadow-sm hover:shadow-xl transition-all"
            >
              <div className="flex justify-between items-start mb-10">
                <div>
                  <h4 className="text-xl font-bold text-zinc-400 mb-1">For Twitter/X Creators</h4>
                  <div className="text-4xl font-black">Postwise</div>
                </div>
                <div className="text-5xl font-black text-zinc-300">5.8</div>
              </div>
              <p className="text-zinc-500 text-lg mb-8 leading-relaxed font-medium">
                If you primarily want to grow a Twitter audience and LinkedIn is secondary, Postwise is decent. For LinkedIn — Velank wins.
              </p>
               <div className="mt-12 space-y-4 pt-10 border-t border-zinc-100">
                <div className="flex gap-3 text-zinc-400 font-medium">
                  <X className="w-5 h-5 shrink-0 text-red-400" />
                  <span>Twitter-centric AI training data</span>
                </div>
                <div className="flex gap-3 text-zinc-400 font-medium">
                  <X className="w-5 h-5 shrink-0 text-red-400" />
                  <span>No LinkedIn analytics or knowledge base</span>
                </div>
              </div>
            </motion.div>
          </div>
        </div>
      </section>

      {/* 4. Origin Myth Check */}
      <section className="py-32 bg-zinc-50 relative overflow-hidden">
        <div className="container mx-auto px-6 max-w-6xl">
          <div className="text-center mb-24">
            <h2 className="text-indigo-600 font-bold tracking-[0.3em] uppercase text-[10px] mb-4">The Truth about Postwise</h2>
            <h3 className="text-4xl md:text-6xl font-black text-zinc-900 tracking-tight leading-[1.05]">
              A Twitter tool with a <br className="hidden md:block"/> <span className="text-sky-500 italic">LinkedIn paint job.</span>
            </h3>
            <p className="text-xl text-zinc-600 mt-8 font-medium max-w-2xl mx-auto">
              Every design choice, AI model, and feature in Postwise was built for the fast-paced, short-form nature of Twitter/X. LinkedIn requires depth, expertise, and authority.
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="bg-white p-8 rounded-3xl border border-zinc-200">
              <Twitter className="w-8 h-8 text-sky-400 mb-6" />
              <h4 className="text-lg font-bold mb-2">Twitter Original</h4>
              <p className="text-sm text-zinc-500 font-medium">AI training models are optimized for punchy hooks and viral Twitter threads, not B2B LinkedIn authority.</p>
            </div>
            <div className="bg-white p-8 rounded-3xl border border-zinc-200">
              <Brain className="w-8 h-8 text-red-400 mb-6" />
              <h4 className="text-lg font-bold mb-2">Knowledge Gap</h4>
              <p className="text-sm text-zinc-500 font-medium">Generates from topics and prompts only. There&apos;s no way to upload your PDFs or whitepapers.</p>
            </div>
            <div className="bg-white p-8 rounded-3xl border border-zinc-200">
              <BarChart3 className="w-8 h-8 text-amber-400 mb-6" />
              <h4 className="text-lg font-bold mb-2">Analytic Blindness</h4>
              <p className="text-sm text-zinc-500 font-medium">No meaningful LinkedIn analytics. You can schedule, but you can&apos;t measure what&apos;s driving DMs.</p>
            </div>
            <div className="bg-white p-8 rounded-3xl border border-zinc-200">
              <ShieldCheck className="w-8 h-8 text-indigo-400 mb-6" />
              <h4 className="text-lg font-bold mb-2">No Guardrails</h4>
              <p className="text-sm text-zinc-500 font-medium">Postwise doesn&apos;t verify facts. It will invent statistics about your company if they sound convincing.</p>
            </div>
          </div>
        </div>
      </section>

      {/* 5. Pricing Comparison */}
      <section className="py-32 bg-white relative overflow-hidden">
        <div className="container mx-auto px-6 max-w-6xl">
          <div className="text-center mb-24">
            <h2 className="text-indigo-600 font-bold tracking-[0.3em] uppercase text-[10px] mb-4">Financial Delta</h2>
            <h3 className="text-4xl md:text-6xl font-black text-zinc-900 tracking-tight leading-tight">
              Pay for value, <br className="hidden md:block"/> <span className="text-indigo-600">not for legacy.</span>
            </h3>
          </div>

          <div className="grid lg:grid-cols-2 gap-12">
             {/* Postwise PRICING */}
             <div className="space-y-4">
              <h4 className="text-2xl font-black mb-8 flex items-center gap-3">
                Postwise <span className="text-zinc-400 italic">&quot;Twitter Focus&quot;</span>
              </h4>
              <div className="p-8 bg-zinc-50 border border-zinc-200 rounded-3xl shadow-sm">
                <div className="flex justify-between items-center mb-2">
                  <span className="font-bold text-zinc-900">Rising Star</span>
                  <span className="text-xl font-black text-zinc-400">$37/mo</span>
                </div>
                <p className="text-sm text-zinc-500 font-medium">400 posts · 3 accounts.</p>
              </div>
              
              <div className="p-8 bg-white border-2 border-zinc-100 rounded-3xl relative shadow-sm">
                <div className="flex justify-between items-center mb-2">
                  <span className="font-bold text-zinc-900">Boss</span>
                  <span className="text-xl font-black text-zinc-900">$59/mo</span>
                </div>
                <p className="text-sm text-zinc-500 font-medium">1,000 posts · GhostWriter tech.</p>
              </div>
              
              <div className="p-8 bg-zinc-900 text-white rounded-3xl relative shadow-2xl border-2 border-zinc-800">
                <div className="flex justify-between items-center mb-2">
                  <span className="font-bold">Unlimited</span>
                  <span className="text-2xl font-black">$97/mo</span>
                </div>
                <p className="text-zinc-400 text-sm mb-4">Unlimited AI credits · Cross-platform.</p>
              </div>
              
              <div className="p-6 bg-red-50 rounded-2xl border border-red-100 mt-8">
                <p className="text-sm text-red-600 font-bold leading-relaxed">
                  ⚠️ No knowledge base at any price. No meaningful LinkedIn analytics. Twitter-first UI.
                </p>
              </div>
            </div>

            {/* Velank PRICING */}
            <div className="space-y-4">
              <h4 className="text-2xl font-black mb-8 flex items-center gap-3">
                Velank AI <span className="text-indigo-600 italic">&quot;LinkedIn First&quot;</span>
              </h4>
              <div className="p-8 bg-white border border-zinc-200 rounded-3xl shadow-sm">
                <div className="flex justify-between items-center mb-2">
                  <span className="font-bold text-zinc-900">Free Forever</span>
                  <span className="text-xl font-black text-emerald-600">$0</span>
                </div>
                <p className="text-sm text-zinc-500 font-medium">3 full AI drafts from your docs · no card ever.</p>
              </div>
              
              <div className="p-8 bg-white text-zinc-900 rounded-3xl relative shadow-2xl border-2 border-indigo-600">
                <div className="absolute top-0 right-10 -translate-y-1/2 bg-indigo-600 text-white text-[10px] font-black px-4 py-1 rounded-full uppercase tracking-widest">Recommended</div>
                <div className="flex justify-between items-center mb-2">
                  <span className="font-bold text-xl">Pro (Monthly)</span>
                  <span className="text-2xl font-black text-indigo-600">$29/mo</span>
                </div>
                <p className="text-zinc-500 text-sm mb-4">Unlimited posts · Knowledge base · Analytics included.</p>
                <div className="h-1 w-full bg-indigo-100 rounded-full overflow-hidden">
                  <div className="h-full bg-indigo-600 w-full" />
                </div>
              </div>
              
              <div className="p-8 bg-indigo-600 text-white rounded-3xl shadow-xl">
                <div className="flex justify-between items-center mb-2">
                  <span className="font-bold text-xl">Annual Plan</span>
                  <span className="text-2xl font-black">$199/yr</span>
                </div>
                <p className="text-indigo-100 text-sm font-medium italic">Unlimited everything · Equivalent to $17/mo.</p>
              </div>
              
              <div className="p-6 bg-emerald-50 rounded-2xl border border-emerald-100 mt-8">
                <p className="text-sm text-emerald-600 font-bold leading-relaxed">
                  ✓ Velank is 50% cheaper than Postwise Boss and offers LinkedIn-specific tech they don&apos;t have.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 6. Feature Comparison Table */}
      <section id="feature-table" className="py-32 bg-white relative">
        <div className="container mx-auto px-6 max-w-5xl">
          <div className="text-center mb-20">
            <h2 className="text-4xl md:text-5xl font-black text-zinc-900 tracking-tighter">Feature by feature.</h2>
          </div>

          <div className="overflow-x-auto rounded-[2.5rem] border border-zinc-200">
            <table className="w-full text-left bg-white border-collapse min-w-[700px]">
              <thead>
                <tr className="border-b border-zinc-100">
                  <th className="p-8 text-xs font-bold text-zinc-400 uppercase tracking-widest">Comparison</th>
                  <th className="p-8 text-sm font-bold text-zinc-400 uppercase tracking-widest">Postwise Boss</th>
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
                      {item.postwise === true ? (
                        <div className="flex items-center gap-2 text-zinc-900 font-semibold"><Check className="w-5 h-5 text-zinc-300" /> Yes</div>
                      ) : item.postwise === false ? (
                        <div className="flex items-center gap-2 text-zinc-300"><X className="w-5 h-5 text-red-200" /> No</div>
                      ) : (
                        <div className="font-bold text-zinc-500 italic uppercase text-[10px]">{item.postwise}</div>
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
        </div>
      </section>

      {/* 7. Deep Dive Reasons */}
      <section className="py-32 bg-zinc-900 text-white relative overflow-hidden">
        <div className="absolute inset-0 bg-brand-mesh opacity-10 pointer-events-none" />
        <div className="container mx-auto px-6 max-w-6xl relative z-10">
          <div className="mb-24">
             <h2 className="text-4xl md:text-6xl font-black tracking-tight mb-4">Why switch?</h2>
             <p className="text-xl text-zinc-400 max-w-2xl font-medium">The 4 things Postwise lacks for serious LinkedIn players.</p>
          </div>

          <div className="grid md:grid-cols-2 gap-12">
            <div className="space-y-12">
              <div className="group">
                <div className="text-indigo-500 font-black text-6xl mb-6 opacity-20 group-hover:opacity-100 transition-opacity">01</div>
                <h4 className="text-2xl font-bold mb-4">It generates from prompts, not expertise</h4>
                <p className="text-zinc-400 leading-relaxed font-medium">
                  Postwise generates from generic topics. It has no access to your docs or case studies. The result is content that sounds like you, but says absolutely nothing unique. Velank uses your real data.
                </p>
              </div>
              <div className="group">
                <div className="text-indigo-500 font-black text-6xl mb-6 opacity-20 group-hover:opacity-100 transition-opacity">02</div>
                <h4 className="text-2xl font-bold mb-4">No LinkedIn performance loops</h4>
                <p className="text-zinc-400 leading-relaxed font-medium">
                  Postwise reviewers consistently note the same thing: no real LinkedIn analytics. You&apos;re posting into a void. Velank shows you exactly which posts drive profile visits and connections.
                </p>
              </div>
            </div>
            <div className="space-y-12 md:pt-24">
              <div className="group">
                <div className="text-indigo-500 font-black text-6xl mb-6 opacity-20 group-hover:opacity-100 transition-opacity">03</div>
                <h4 className="text-2xl font-bold mb-4">Fixed output with no refinement</h4>
                <p className="text-zinc-400 leading-relaxed font-medium">
                  Once Postwise generates a post, there&apos;s no way to ask the AI to &quot;make it punchier&quot; or &quot;add a CTA.&quot; Every edit is manual frustration. Velank treats the draft as a conversation you can refine.
                </p>
              </div>
              <div className="group">
                <div className="text-indigo-500 font-black text-6xl mb-6 opacity-20 group-hover:opacity-100 transition-opacity">04</div>
                <h4 className="text-2xl font-bold mb-4">Platform mismatch risks</h4>
                <p className="text-zinc-400 leading-relaxed font-medium">
                  Twitter engagement patterns and LinkedIn success metrics are fundamentally different. Postwise optimizes for viral Twitter threads. Velank optimizes for deep B2B authority.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 8. Testimonials */}
      <section className="py-32 bg-white relative">
        <div className="container mx-auto px-6 max-w-6xl">
           <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
             <div className="bg-zinc-50 p-8 rounded-[2.5rem] border border-zinc-100 flex flex-col justify-between">
                <div>
                  <div className="flex text-amber-500 gap-1 mb-6">
                    {[1,2,3,4,5].map(i => <Sparkles key={i} className="w-4 h-4 fill-current" />)}
                  </div>
                  <p className="text-zinc-700 font-medium leading-relaxed italic mb-8">
                    &quot;Postwise was fine for Twitter but my LinkedIn content felt hollow. Velank reads my actual consulting proposals and generates posts that actually sound like me.&quot;
                  </p>
                </div>
                <div className="flex items-center gap-4 border-t border-zinc-200 pt-6">
                  <div className="w-10 h-10 rounded-full bg-indigo-600 flex items-center justify-center text-white font-black text-xs">AC</div>
                  <div>
                    <div className="text-sm font-black">Anita C.</div>
                    <div className="text-[10px] uppercase font-bold text-zinc-400">Strategy Consultant</div>
                  </div>
                </div>
             </div>

             <div className="bg-indigo-50/50 p-8 rounded-[2.5rem] border border-indigo-100/50 flex flex-col justify-between scale-105 shadow-xl shadow-indigo-100/20 relative z-10">
                <div>
                  <div className="flex text-indigo-500 gap-1 mb-6">
                    {[1,2,3,4,5].map(i => <Award key={i} className="w-4 h-4 fill-current" />)}
                  </div>
                  <p className="text-zinc-800 font-bold leading-relaxed mb-8">
                    &quot;I moved to Velank from Postwise and saw 3 inbound leads in my first month. The knowledge base feature is why this tool wins for LinkedIn.&quot;
                  </p>
                </div>
                <div className="flex items-center gap-4 border-t border-indigo-100 pt-6">
                  <div className="w-10 h-10 rounded-full bg-indigo-600 flex items-center justify-center text-white font-black text-xs">TP</div>
                  <div>
                    <div className="text-sm font-black">Thomas P.</div>
                    <div className="text-[10px] uppercase font-bold text-indigo-400 text-zinc-400">SaaS Founder</div>
                  </div>
                </div>
             </div>

             <div className="bg-zinc-50 p-8 rounded-[2.5rem] border border-zinc-100 flex flex-col justify-between">
                <div>
                  <div className="flex text-amber-500 gap-1 mb-6">
                    {[1,2,3,4,5].map(i => <Zap key={i} className="w-4 h-4 fill-current" />)}
                  </div>
                  <p className="text-zinc-700 font-medium leading-relaxed italic mb-8">
                    &quot;The analytics alone made Velank worth it. With Postwise I was just posting into a void. Velank shows me which posts actually drive visits.&quot;
                  </p>
                </div>
                <div className="flex items-center gap-4 border-t border-zinc-200 pt-6">
                  <div className="w-10 h-10 rounded-full bg-zinc-900 flex items-center justify-center text-white font-black text-xs">MV</div>
                  <div>
                    <div className="text-sm font-black">Maya V.</div>
                    <div className="text-[10px] uppercase font-bold text-zinc-400">Fractional CMO</div>
                  </div>
                </div>
             </div>
           </div>
        </div>
      </section>

      {/* 9. Final CTA */}
      <section className="py-40 bg-zinc-900">
        <div className="container mx-auto px-6 max-w-5xl text-center">
            <h2 className="text-4xl md:text-7xl font-black text-white mb-8 tracking-tighter leading-tight">
              LinkedIn deserves a tool <br className="hidden md:block"/> <span className="text-indigo-600 italic">built for authority.</span>
            </h2>
            <p className="text-xl text-zinc-400 mb-12 max-w-2xl mx-auto font-medium leading-relaxed">
              Upload one document, generate your first grounded post, and see exactly what Postwise can&apos;t do.
            </p>
            
            <div className="flex flex-col items-center gap-8">
              <MagneticButton>
                <Link href="https://app.velank.io/login" className="inline-flex items-center justify-center rounded-2xl font-black transition-all bg-indigo-600 text-white hover:bg-indigo-700 h-16 md:h-20 px-8 md:px-12 text-lg md:text-xl shadow-2xl transform active:scale-95 group">
                  Start Free — Try Velank Now <ArrowRight className="ml-3 w-5 h-5 group-hover:translate-x-1 transition-transform" />
                </Link>
              </MagneticButton>
              <Link href="/pricing" className="text-zinc-400 hover:text-white transition-colors font-bold text-lg">See pricing →</Link>
              <p className="text-xs font-bold text-zinc-600 uppercase tracking-widest mt-4">
                Free forever plan · Pro at $29/mo · No credit card ever
              </p>
            </div>
        </div>
      </section>

      <Footer />
    </div>
  );
}
