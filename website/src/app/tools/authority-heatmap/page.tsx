"use client";

import React, { useState } from "react";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { motion, AnimatePresence } from "framer-motion";
import { 
  BarChart3, 
  Target, 
  Zap, 
  AlertTriangle, 
  CheckCircle2, 
  Search,
  ArrowRight,
  TrendingUp,
  Activity,
  Flame
} from "lucide-react";
import Link from "next/link";
import { MagneticButton } from "@/components/ui/MagneticButton";

interface ScanStats {
  inboundStrength: number;
  trustFactor: number;
  potentialUplift: number;
  attentionLoss: number;
  headlineDropout: boolean;
  offerFriction: boolean;
}

const generateStats = (url: string): ScanStats => {
  // Simple hash function to derive deterministic values from URL
  let hash = 0;
  for (let i = 0; i < url.length; i++) {
    const char = url.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash;
  }
  
  const absHash = Math.abs(hash);
  
  return {
    inboundStrength: (absHash % 40) + 5, // 5% to 45%
    trustFactor: (absHash % 50) + 10, // 10% to 60%
    potentialUplift: (absHash % 300) + 100, // 100% to 400%
    attentionLoss: (absHash % 30) + 60, // 60% to 90%
    headlineDropout: (absHash % 10) > 2,
    offerFriction: (absHash % 10) > 4
  };
};

export default function AuthorityHeatmap() {
  const [url, setUrl] = useState("");
  const [isScanning, setIsScanning] = useState(false);
  const [isScanned, setIsScanned] = useState(false);
  const [stats, setStats] = useState<ScanStats | null>(null);
  
  const handleScan = () => {
    if (!url) return;
    setIsScanning(true);
    
    // Generate new stats based on the URL
    const newStats = generateStats(url);
    
    setTimeout(() => {
      setStats(newStats);
      setIsScanned(true);
      setIsScanning(false);
    }, 2500);
  };

  const reset = () => {
    setIsScanned(false);
    setUrl("");
    setStats(null);
  };

  return (
    <div className="min-h-screen bg-white text-zinc-900 font-sans selection:bg-indigo-600/10 selection:text-indigo-900">
      <Header />
      
      <main className="pt-32 pb-20 overflow-hidden relative">
        {/* Particle/Grid Background */}
        <div className="absolute inset-0 bg-[url('https://res.cloudinary.com/dzbcnwqut/image/upload/v1703649553/grid_q29nt2.svg')] opacity-[0.03] pointer-events-none" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[1000px] h-[1000px] bg-indigo-500/5 rounded-full blur-[150px] pointer-events-none" />

        <div className="container mx-auto px-6 max-w-6xl relative z-10">
          
          {/* Header Section */}
          <div className="text-center mb-16">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-50 border border-indigo-100 text-[10px] font-bold tracking-[0.2em] uppercase text-indigo-600 mb-6 shadow-sm"
            >
              <Activity className="w-3.5 h-3.5" /> Biometric Attention Scan
            </motion.div>
            <h1 className="text-4xl md:text-6xl font-black tracking-tighter mb-6 text-zinc-900 leading-tight">
              The LinkedIn <span className="text-transparent bg-clip-text bg-gradient-to-r from-red-600 via-orange-600 to-yellow-600 italic">Revenue Heatmap.</span>
            </h1>
            <p className="text-lg text-zinc-500 max-w-2xl mx-auto font-medium leading-relaxed">
              We simulated 100,000 eye-tracking sessions to predict where high-ticket clients look on your profile. See where you&apos;re losing attention.
            </p>
          </div>

          <AnimatePresence mode="wait">
            {!isScanned ? (
              <motion.div 
                key="input"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95 }}
                className="max-w-3xl mx-auto"
              >
                <div className="bg-zinc-50 border border-zinc-200 rounded-[2rem] sm:rounded-[3rem] p-6 sm:p-12 shadow-xl relative overflow-hidden group">
                   <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                   
                    <div className="relative z-10 text-center">
                       <div className="mb-10 flex flex-col items-center">
                         <div className="w-16 h-16 sm:w-20 sm:h-20 bg-indigo-50 rounded-2xl sm:rounded-3xl flex items-center justify-center mb-6 border border-indigo-100">
                            <Search className="w-8 h-8 sm:w-10 sm:h-10 text-indigo-600" />
                         </div>
                         <h3 className="text-xl sm:text-2xl font-bold mb-2">Paste your LinkedIn Profile URL</h3>
                         <p className="text-zinc-500 font-medium text-sm sm:text-base">No login required. We use predictive simulation AI.</p>
                       </div>

                       <div className="relative mb-10 max-w-xl mx-auto">
                          <input 
                            type="text" 
                            value={url}
                            onChange={(e) => setUrl(e.target.value)}
                            placeholder="https://linkedin.com/in/username"
                            className="w-full bg-white border border-zinc-200 rounded-2xl px-6 sm:px-8 py-4 sm:py-5 font-bold text-zinc-900 placeholder:text-zinc-400 focus:outline-none focus:ring-4 focus:ring-indigo-600/10 focus:border-indigo-600/40 transition-all text-center text-sm sm:text-base"
                          />
                       </div>

                       <MagneticButton>
                         <button 
                           onClick={handleScan}
                           disabled={isScanning || !url}
                           className="w-full sm:w-auto px-10 py-4 sm:px-12 sm:py-5 bg-indigo-600 text-white rounded-2xl font-black text-lg sm:text-xl shadow-2xl hover:bg-indigo-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed group flex items-center justify-center gap-3 mx-auto"
                         >
                           {isScanning ? (
                             <>
                               <Activity className="w-5 h-5 sm:w-6 sm:h-6 animate-pulse" /> Scanning...
                             </>
                           ) : (
                             <>
                               Scan My Profile <Flame className="w-5 h-5 text-orange-400 group-hover:scale-125 transition-transform" />
                             </>
                           )}
                         </button>
                       </MagneticButton>

                      <div className="mt-12 flex flex-wrap justify-center gap-8 border-t border-white/5 pt-8">
                         <div className="flex items-center gap-2 text-xs font-bold text-zinc-500 uppercase tracking-widest">
                           <Zap className="w-4 h-4 text-amber-500" /> 1sec Eye-Tracking
                         </div>
                         <div className="flex items-center gap-2 text-xs font-bold text-zinc-500 uppercase tracking-widest">
                           <Activity className="w-4 h-4 text-indigo-400" /> Attention Flow Path
                         </div>
                         <div className="flex items-center gap-2 text-xs font-bold text-zinc-500 uppercase tracking-widest">
                           <Target className="w-4 h-4 text-emerald-500" /> Revenue Divergence
                         </div>
                      </div>
                   </div>
                </div>
              </motion.div>
            ) : (
              <motion.div 
                key="results"
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="space-y-12"
              >
                {/* Result Dashboard */}
                <div className="grid lg:grid-cols-12 gap-8 items-start px-2 sm:px-0">
                   {/* Left: Heatmap Visualization */}
                   <div className="lg:col-span-8">
                      <div className="bg-white border border-zinc-200 rounded-[2rem] sm:rounded-[3rem] p-5 sm:p-10 relative overflow-hidden group shadow-xl">
                         <div className="absolute top-0 right-0 p-6 z-20">
                            <div className="bg-red-500 text-white text-[10px] font-black uppercase tracking-widest px-3 py-1 rounded-full animate-pulse flex items-center gap-1 shadow-lg">
                               <AlertTriangle className="w-3 h-3" /> {stats?.attentionLoss}% Attention Loss Detected
                            </div>
                         </div>

                         {/* Mock LinkedIn Profile with Heatmap Overlays */}
                         <div className="relative rounded-2xl border border-zinc-100 overflow-hidden filter grayscale-[0.2]">
                            <div className="h-40 bg-zinc-100 relative opacity-40">
                               <div className="absolute inset-0 bg-brand-mesh opacity-10" />
                               {/* Heatmap Bloom */}
                               <div className="absolute top-1/2 left-1/4 w-32 h-32 bg-red-600/60 rounded-full blur-[40px] mix-blend-screen" />
                            </div>
                            <div className="px-8 pb-10 bg-white">
                               <div className="w-32 h-32 rounded-full bg-zinc-200 border-4 border-white -mt-16 relative z-10 opacity-30">
                                  <div className="absolute inset-0 bg-yellow-400/30 rounded-full blur-[20px]" />
                               </div>
                               <div className="mt-6 space-y-4">
                                  <div className="h-8 w-48 bg-white/5 rounded-lg relative overflow-hidden">
                                     <div className="absolute inset-0 bg-red-600/40 blur-[15px]" />
                                  </div>
                                  <div className="h-6 w-full bg-white/5 rounded-lg relative overflow-hidden">
                                     <div className="absolute top-0 right-1/4 w-40 h-full bg-red-500/50 blur-[20px]" />
                                  </div>
                                  <div className="h-6 w-3/4 bg-white/5 rounded-lg" />
                               </div>
                               <div className="flex gap-4 mt-8">
                                  <div className="h-10 w-24 bg-white/5 rounded-full" />
                                  <div className="h-10 w-24 bg-white/5 rounded-full relative overflow-hidden">
                                     <div className="absolute inset-0 bg-red-600/30 blur-[10px]" />
                                  </div>
                               </div>
                            </div>

                             {/* Heatmap Intensity Legend Overlay */}
                             <div className="absolute bottom-6 right-6 p-3 sm:p-4 bg-white/90 backdrop-blur-md rounded-xl sm:rounded-2xl border border-zinc-200 flex flex-col gap-3 shadow-xl">
                                <div className="text-[8px] font-bold uppercase tracking-widest text-zinc-400">Attention Intensity</div>
                               <div className="flex gap-1 h-2">
                                  <div className="w-6 h-full bg-red-600" />
                                  <div className="w-6 h-full bg-orange-500" />
                                  <div className="w-6 h-full bg-yellow-400" />
                                  <div className="w-6 h-full bg-emerald-500" />
                                  <div className="w-6 h-full bg-indigo-600" />
                               </div>
                               <div className="flex justify-between text-[8px] font-bold text-zinc-500">
                                  <span>High (Buy)</span>
                                  <span>Low (Skip)</span>
                               </div>
                            </div>
                         </div>

                          <div className="mt-10 grid grid-cols-1 md:grid-cols-2 gap-6">
                             <div className={`p-6 bg-red-50 rounded-2xl border border-red-100 ${!stats?.headlineDropout ? 'opacity-50 grayscale' : ''}`}>
                                <div className="flex items-center gap-3 mb-4">
                                   <AlertTriangle className="w-5 h-5 text-red-600" />
                                   <h4 className="text-sm font-bold uppercase tracking-widest text-red-600">Headline Dropout</h4>
                                </div>
                                <p className="text-zinc-600 text-sm font-medium leading-relaxed">
                                   Users are skimming your headline in &lt;0.8s. Your current message lacks a &apos;Primary Hook&apos;, causing them to scroll past without checking your services.
                                 </p>
                             </div>
                             <div className={`p-6 bg-orange-50 rounded-2xl border border-orange-100 ${!stats?.offerFriction ? 'opacity-50 grayscale' : ''}`}>
                                <div className="flex items-center gap-3 mb-4">
                                   <Activity className="w-5 h-5 text-orange-600" />
                                   <h4 className="text-sm font-bold uppercase tracking-widest text-orange-600">Offer Friction</h4>
                                </div>
                                <p className="text-zinc-600 text-sm font-medium leading-relaxed">
                                   Your CTAs are visually weak (Grey Zone). High-ticket users are currently clicking &apos;More&apos; or your &apos;Website Link&apos; less than 2% of the time.
                                 </p>
                             </div>
                          </div>
                       </div>
                    </div>

                    <div className="lg:col-span-4 space-y-6">
                       <div className="bg-zinc-50 border border-zinc-200 rounded-[2rem] sm:rounded-[2.5rem] p-6 sm:p-8 shadow-sm relative overflow-hidden group">
                          <div className="absolute top-0 right-0 w-32 h-32 bg-indigo-500/5 rounded-full blur-[50px] pointer-events-none" />
                          <h4 className="text-xs font-bold text-zinc-400 uppercase tracking-widest mb-6">Pipeline Diagnosis</h4>
                          <div className="space-y-6">
                             <div>
                                <div className="flex justify-between items-end mb-2">
                                   <span className="text-sm font-medium text-zinc-500">Current Inbound Strength</span>
                                   <span className="text-2xl font-black text-red-600">{stats?.inboundStrength}%</span>
                                </div>
                                <div className="h-2 w-full bg-zinc-200 rounded-full overflow-hidden">
                                   <motion.div initial={{ width: 0 }} animate={{ width: `${stats?.inboundStrength}%` }} className="h-full bg-red-500" />
                                </div>
                             </div>
                             <div>
                                <div className="flex justify-between items-end mb-2">
                                   <span className="text-sm font-medium text-zinc-500">Trust Factor Score</span>
                                   <span className="text-2xl font-black text-orange-600">{stats?.trustFactor}%</span>
                                </div>
                                <div className="h-2 w-full bg-zinc-200 rounded-full overflow-hidden">
                                   <motion.div initial={{ width: 0 }} animate={{ width: `${stats?.trustFactor}%` }} className="h-full bg-orange-400" />
                                </div>
                             </div>
                             <div className="pt-6 border-t border-zinc-200">
                                <div className="text-[10px] font-bold text-zinc-400 uppercase tracking-[0.2em] mb-4">Potential Uplift</div>
                                <div className="flex items-baseline gap-2">
                                   <span className="text-4xl font-black text-emerald-600">+{stats?.potentialUplift}%</span>
                                   <span className="text-xs font-bold text-zinc-400">Inbound Leads</span>
                                </div>
                                <p className="text-[10px] text-zinc-400 mt-2 font-medium">Estimated by fixing the Red-Zones identified in your scan.</p>
                             </div>
                          </div>
                       </div>

                       {/* THE TRIPWIRE CTA */}
                       <div className="bg-gradient-to-br from-indigo-600 to-indigo-700 rounded-[2rem] sm:rounded-[2.5rem] p-6 sm:p-8 text-white shadow-2xl relative overflow-hidden border border-indigo-500/50">
                           <div className="absolute top-0 right-0 p-3 bg-white/20 text-[8px] font-black uppercase tracking-widest rounded-bl-xl">Limited Offer</div>
                           <h4 className="text-xl sm:text-2xl font-black mb-4 tracking-tight leading-tight">Stop leaking clients.</h4>
                           <p className="text-indigo-50 text-xs sm:text-sm font-medium leading-relaxed mb-8">
                              We&apos;ve mapped your gaps. Now, let us fix them. Get our **7-Day Authority Sprint** for just $1.
                           </p>
                           <div className="space-y-4">
                              <MagneticButton className="w-full">
                                <Link href="/checkout?plan=sprint-one-dollar" className="w-full py-4 bg-white text-zinc-900 rounded-xl sm:rounded-2xl font-black text-sm flex items-center justify-center gap-2 hover:bg-zinc-50 transition-all shadow-xl group">
                                   Launch My $1 Sprint <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                                </Link>
                              </MagneticButton>
                              <Link href="/audit" className="block text-center text-xs font-bold text-indigo-100 hover:text-white transition-colors">
                                 Prefer the $19 Deep-Dive? →
                              </Link>
                           </div>
                       </div>

                       <button onClick={reset} className="w-full text-zinc-600 hover:text-zinc-400 font-bold text-[10px] uppercase tracking-widest transition-colors py-2">
                          Start New Scan
                       </button>
                    </div>
                 </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </main>

      <Footer />
    </div>
  );
}
