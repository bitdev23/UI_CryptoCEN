"use client";

import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { motion } from "framer-motion";
import { CheckCircle2, Zap, ArrowRight, ShieldCheck, BarChart3, Target, Clock, Star, MessageSquare } from "lucide-react";
import Link from "next/link";
import { MagneticButton } from "@/components/ui/MagneticButton";

export default function AuthorityAuditPage() {
  return (
    <div className="min-h-screen bg-white text-zinc-900 font-sans selection:bg-indigo-600/10 selection:text-indigo-900">
      <Header />
      
      <main className="pt-32 pb-20">
        {/* Special Top Urgency Bar */}
        <div className="bg-indigo-50 border-b border-indigo-100 py-3">
          <div className="container mx-auto px-6 text-center">
            <p className="text-xs font-bold tracking-[0.2em] uppercase text-indigo-600 animate-pulse">
              ⚠️ LIMITED CAPACITY: Only 12 Audits Remaining for Today
            </p>
          </div>
        </div>

        {/* Hero Section */}
        <section className="relative py-24 overflow-hidden">
          {/* Background effects */}
          <div className="absolute top-0 right-0 w-[600px] h-[600px] bg-indigo-500/10 rounded-full blur-[120px] pointer-events-none -translate-y-1/2 translate-x-1/2" />
          
          <div className="container mx-auto px-6 max-w-6xl relative z-10">
            <div className="grid lg:grid-cols-2 gap-16 items-center">
              <motion.div
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.6 }}
              >
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-50 border border-indigo-100 text-[10px] font-bold tracking-[0.2em] uppercase text-indigo-600 mb-8">
                  <ShieldCheck className="w-3.5 h-3.5" /> High-Intensity Profile Audit
                </div>
                <h1 className="text-5xl md:text-7xl font-black tracking-tighter mb-8 leading-[1.05]">
                  Stop leaking <br />
                  <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-600 to-indigo-400 italic">Inbound Leads.</span>
                </h1>
                <p className="text-xl text-zinc-500 mb-12 font-medium leading-relaxed max-w-xl">
                  Get a comprehensive, 12-point audit of your LinkedIn presence. We reveal exactly why you aren&apos;t converting followers into high-ticket clients.
                </p>
                
                 <div className="flex flex-col gap-6 mb-12">
                    {[
                      "Profile & Banner " + "Psychology" + " Analysis",
                      "Content-to-Conversion Gap Mapping",
                      "3 Personalized Hook Templates",
                      "24-Hour Delivery"
                    ].map((item, i) => (
                      <div key={i} className="flex items-center gap-4 text-zinc-600 font-bold">
                         <CheckCircle2 className="w-5 h-5 text-indigo-600 shrink-0" />
                         {item}
                      </div>
                    ))}
                 </div>

                <div className="flex flex-col sm:flex-row items-center gap-4">
                  <MagneticButton>
                    <Link href="https://app.velank.io/login" className="inline-flex items-center justify-center rounded-2xl bg-indigo-600 text-white h-16 px-10 text-lg font-black shadow-2xl shadow-indigo-600/30 hover:bg-indigo-700 active:scale-95 transition-all group">
                      Claim My Audit for $19 <ArrowRight className="ml-2 w-5 h-5 group-hover:translate-x-1 transition-transform" />
                    </Link>
                  </MagneticButton>
                  <div className="text-center sm:text-left">
                    <div className="text-xs font-bold text-zinc-500 uppercase tracking-widest mb-1 font-mono">One-Time Payment</div>
                    <div className="text-white font-black text-sm">80% OFF — Ends in 4h</div>
                  </div>
                </div>
              </motion.div>

              {/* Sample Audit Card */}
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.8, delay: 0.2 }}
                className="relative"
              >
                <div className="absolute inset-0 bg-indigo-500/20 blur-[100px] rounded-full pointer-events-none" />
                <div className="bg-white/90 backdrop-blur-xl border border-zinc-200 rounded-[2.5rem] p-8 md:p-10 shadow-2xl relative z-10 overflow-hidden">
                   <div className="flex items-center justify-between mb-8 border-b border-zinc-100 pb-6">
                      <div className="flex items-center gap-3">
                         <div className="w-10 h-10 rounded-xl bg-indigo-600 flex items-center justify-center text-white font-black">V</div>
                         <div className="text-xs font-bold uppercase tracking-widest text-zinc-400">Sample Audit Report</div>
                      </div>
                      <div className="px-3 py-1 rounded-full bg-indigo-50 text-indigo-600 text-[10px] font-black uppercase tracking-widest border border-indigo-100">
                         Confidential
                      </div>
                   </div>

                   <div className="space-y-8">
                      <div>
                        <div className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-3">Authority Score</div>
                        <div className="flex items-baseline gap-2">
                           <span className="text-6xl font-black text-indigo-600 tracking-tighter">64</span>
                           <span className="text-zinc-400 font-bold text-xl">/100</span>
                           <span className="ml-4 text-xs font-bold text-red-600 uppercase bg-red-50 px-2 py-1 rounded">Needs Fixing</span>
                        </div>
                      </div>

                      <div className="grid grid-cols-2 gap-4">
                         <div className="bg-zinc-50 rounded-2xl p-4 border border-zinc-100">
                            <BarChart3 className="w-5 h-5 text-indigo-600 mb-2" />
                            <div className="text-[10px] font-bold text-zinc-400 uppercase mb-1">Curation</div>
                            <div className="text-zinc-900 font-black">Top 12%</div>
                         </div>
                         <div className="bg-zinc-50 rounded-2xl p-4 border border-zinc-100">
                            <Target className="w-5 h-5 text-emerald-600 mb-2" />
                            <div className="text-[10px] font-bold text-zinc-400 uppercase mb-1">Clarity</div>
                            <div className="text-zinc-900 font-black">Weak</div>
                         </div>
                      </div>

                      <div className="space-y-4">
                         <div className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest">Crucial Gaps Found</div>
                         <div className="p-4 bg-red-50 rounded-2xl border border-red-100 text-sm text-zinc-600 font-medium">
                            &quot;Your banner message is too broad. It doesn&apos;t specify the outcome for the ICP. Recommend switching to a data-backed result hook.&quot;
                         </div>
                         <div className="p-4 bg-amber-50 rounded-2xl border border-amber-100 text-sm text-zinc-600 font-medium">
                            &quot;Featured section is outdated. You&apos;re missing a direct &apos;Book Demo&apos; trigger. Current leads are falling off here.&quot;
                         </div>
                      </div>
                   </div>
                </div>

                {/* Decorative floating elements */}
                <motion.div 
                  animate={{ y: [0, -10, 0] }} 
                  transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
                  className="absolute -top-6 -left-6 bg-white border border-zinc-200 p-4 rounded-2xl shadow-2xl z-20"
                >
                   <Star className="w-5 h-5 text-amber-500 mb-1" />
                   <div className="text-[8px] font-bold uppercase tracking-widest text-zinc-400">Industry Rank</div>
                   <div className="text-xs font-black text-zinc-900">#12,504</div>
                </motion.div>
              </motion.div>
            </div>
          </div>
        </section>

        {/* Why $19? Section */}
        <section className="py-32 bg-zinc-50 border-y border-zinc-100">
          <div className="container mx-auto px-6 max-w-4xl text-center">
             <h2 className="text-3xl md:text-5xl font-black text-zinc-900 mb-8 tracking-tighter">Why only $19?</h2>
             <p className="text-xl text-zinc-500 mb-12 font-medium leading-relaxed">
               Frankly, it&apos;s our &quot;Value First&quot; strategy. We know that once you see the gaps in your presence, the choice to use Velank AI for automation becomes a no-brainer. This isn&apos;t a lead magnet — it&apos;s a tactical weapon for your brand.
             </p>
             <div className="grid md:grid-cols-3 gap-8">
                {[
                  { icon: Clock, label: "Fast Delivery", detail: "24h Response Time" },
                  { icon: MessageSquare, label: "Live Q&A", detail: "1-Click Support" },
                  { icon: Zap, label: "Actionable", detail: "Zero Fluff advice" }
                ].map((item, i) => (
                  <div key={i} className="flex flex-col items-center">
                     <div className="w-12 h-12 bg-white rounded-2xl flex items-center justify-center mb-4 border border-zinc-200 text-indigo-600 shadow-sm">
                        <item.icon className="w-6 h-6" />
                     </div>
                     <div className="text-sm font-bold text-zinc-900 mb-1">{item.label}</div>
                     <div className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest">{item.detail}</div>
                  </div>
                ))}
             </div>
          </div>
        </section>

        {/* CTA Band */}
        <section className="py-24 relative overflow-hidden">
           <div className="container mx-auto px-6 max-w-3xl text-center relative z-10">
              <h2 className="text-4xl md:text-6xl font-black text-zinc-900 mb-12 tracking-tighter leading-tight">
                Get your authority <br/> report <span className="text-indigo-600 italic font-serif">by tomorrow.</span>
              </h2>
              <Link href="https://app.velank.io/login" className="inline-flex items-center justify-center rounded-2xl bg-indigo-600 text-white h-16 px-12 text-xl font-black shadow-2xl hover:bg-indigo-700 active:scale-95 transition-all group">
                Claim Audit Now ($19) <ArrowRight className="ml-2 w-5 h-5 group-hover:translate-x-1 transition-transform" />
              </Link>
              <p className="mt-8 text-zinc-400 font-bold uppercase tracking-[0.3em] text-[10px]">
                Safe & Secure • 100% Money Back Guarantee
              </p>
           </div>
        </section>
      </main>

      <Footer />
    </div>
  );
}
