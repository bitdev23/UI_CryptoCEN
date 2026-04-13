"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useState, useEffect } from "react";
import { 
  CheckCircle2, 
  Clock, 
  Database, 
  FileText, 
  Sparkles, 
  LayoutDashboard, 
  MousePointer2,
  Settings,
  Inbox,
  Share2
} from "lucide-react";
import Image from "next/image";

export const HeroMockupSequence = () => {
  const [step, setStep] = useState(0);

  useEffect(() => {
    let timer: NodeJS.Timeout;
    if (step === 0) timer = setTimeout(() => setStep(1), 1500); 
    else if (step === 1) timer = setTimeout(() => setStep(2), 1000); 
    else if (step === 2) timer = setTimeout(() => setStep(3), 2000); 
    else if (step === 3) timer = setTimeout(() => setStep(4), 2000); 
    else if (step === 4) timer = setTimeout(() => setStep(5), 1200); 
    else if (step === 5) timer = setTimeout(() => setStep(6), 1200); 
    else if (step === 6) timer = setTimeout(() => setStep(7), 1200); 
    else if (step === 7) timer = setTimeout(() => setStep(8), 1200); 
    else if (step === 8) timer = setTimeout(() => setStep(0), 5000); 
    return () => clearTimeout(timer);
  }, [step]);

  return (
    <div className="w-full lg:flex-1 relative z-10 flex justify-center lg:justify-center py-4">
      <style jsx global>{`
        .no-scrollbar-mockup::-webkit-scrollbar { display: none !important; }
        .no-scrollbar-mockup { -ms-overflow-style: none !important; scrollbar-width: none !important; }
      `}</style>

      {/* Ambiance Glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[140%] h-[140%] bg-indigo-500/5 rounded-full blur-[140px] pointer-events-none" />

      {/* Global Scaling Container - Adjusted for mobile readability & desktop presence */}
      <div className="relative w-full max-w-[340px] sm:max-w-[960px] scale-[1.05] sm:scale-[0.6] md:scale-[0.7] lg:scale-[0.65] xl:scale-[0.7] 2xl:scale-[0.8] origin-center transition-all duration-1000 ease-in-out">
        
        {/* Sequential Toast Notifications - Balanced for mobile & desktop */}
        <div className="absolute right-4 sm:-right-6 lg:-right-8 top-16 flex flex-col gap-3 z-[100] pointer-events-none scale-90 origin-right">
          <AnimatePresence>
            {step >= 5 && (
              <motion.div 
                key="toast-1" initial={{ opacity: 0, x: 40, scale: 0.9 }} animate={{ opacity: 1, x: 0, scale: 1 }} exit={{ opacity: 0, scale: 0.9 }}
                className="bg-white/95 backdrop-blur-xl rounded-[20px] shadow-[0_15px_45px_rgba(0,0,0,0.08)] border border-white/20 p-4 flex items-center gap-3.5 w-[260px] ring-1 ring-black/[0.03]"
              >
                <div className="w-9 h-9 rounded-full bg-indigo-50 flex items-center justify-center shrink-0 border border-indigo-100/50">
                  <FileText className="w-4.5 h-4.5 text-[#635BFF]" />
                </div>
                <div className="flex flex-col">
                  <span className="text-[10px] font-black text-zinc-900 uppercase tracking-widest leading-none">file updated</span>
                  <span className="text-[9px] text-zinc-400 mt-1 font-medium">Successfully processed</span>
                </div>
              </motion.div>
            )}
            {step >= 6 && (
              <motion.div 
                key="toast-2" initial={{ opacity: 0, x: 40, scale: 0.9 }} animate={{ opacity: 1, x: 0, scale: 1 }} exit={{ opacity: 0, scale: 0.9 }}
                className="bg-white/95 backdrop-blur-xl rounded-[20px] shadow-[0_15px_45px_rgba(0,0,0,0.08)] border border-white/20 p-4 flex items-center gap-3.5 w-[260px] ring-1 ring-black/[0.03]"
              >
                <div className="w-9 h-9 rounded-full bg-emerald-50 flex items-center justify-center shrink-0 border border-emerald-100/50">
                  <Database className="w-4.5 h-4.5 text-emerald-600" />
                </div>
                <div className="flex flex-col">
                  <span className="text-[10px] font-black text-zinc-900 uppercase tracking-widest leading-none">data base trained</span>
                  <span className="text-[9px] text-zinc-400 mt-1 font-medium">344 chunks indexed</span>
                </div>
              </motion.div>
            )}
            {step >= 7 && (
              <motion.div 
                key="toast-3" initial={{ opacity: 0, x: 40, scale: 0.9 }} animate={{ opacity: 1, x: 0, scale: 1 }} exit={{ opacity: 0, scale: 0.9 }}
                className="bg-white/95 backdrop-blur-xl rounded-[20px] shadow-[0_15px_45px_rgba(0,0,0,0.08)] border border-white/20 p-4 flex items-center gap-3.5 w-[260px] ring-1 ring-black/[0.03]"
              >
                <div className="w-9 h-9 rounded-full bg-amber-50 flex items-center justify-center shrink-0 border border-amber-100/50">
                  <Clock className="w-4.5 h-4.5 text-amber-600" />
                </div>
                <div className="flex flex-col">
                  <span className="text-[10px] font-black text-zinc-900 uppercase tracking-widest leading-none">post scheduled</span>
                  <span className="text-[9px] text-zinc-400 mt-1 font-medium">Tomorrow at 9:00 AM</span>
                </div>
              </motion.div>
            )}
            {step >= 8 && (
              <motion.div 
                key="toast-4" initial={{ opacity: 0, x: 40, scale: 0.9 }} animate={{ opacity: 1, x: 0, scale: 1 }} exit={{ opacity: 0, scale: 0.9 }}
                className="bg-zinc-900 rounded-[20px] shadow-[0_20px_55px_rgba(99,91,255,0.35)] border border-white/10 p-4 flex items-center gap-3.5 w-[260px]"
              >
                <div className="w-9 h-9 rounded-full bg-[#635BFF] flex items-center justify-center shrink-0 border border-white/20">
                  <Share2 className="w-4.5 h-4.5 text-white" />
                </div>
                <div className="flex flex-col">
                  <span className="text-[10px] font-black text-white uppercase tracking-widest leading-none">posted on linkedin</span>
                  <span className="text-[9px] text-white/40 mt-1 font-medium">Live and engaging</span>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Browser Dashboard Frame - Transforms into Sleek Device Frame on mobile */}
        <motion.div 
          className="bg-white rounded-[32px] sm:rounded-[24px] shadow-[0_45px_120px_-30px_rgba(0,0,0,0.15),0_0_0_1px_rgba(0,0,0,0.02)] flex flex-col relative w-full h-[620px] sm:h-[600px] overflow-hidden border-[1px] sm:border-0 border-zinc-200 shadow-2xl ring-8 ring-zinc-100 sm:ring-0"
        >
          {/* Top Address Bar - Simplified on mobile to look like Status Bar */}
          <div className="w-full h-12 sm:h-11 bg-zinc-50/80 backdrop-blur-sm border-b border-zinc-200/50 flex items-center px-6 shrink-0 relative z-50">
            <div className="flex gap-2">
              <div className="w-2.5 h-2.5 rounded-full bg-[#FF5F57] shadow-inner opacity-80" />
              <div className="w-2.5 h-2.5 rounded-full bg-[#FEBC2E] shadow-inner opacity-80" />
              <div className="w-2.5 h-2.5 rounded-full bg-[#28C840] shadow-inner opacity-80" />
            </div>
            <div className="hidden sm:flex flex-1 max-w-[340px] mx-auto h-6.5 bg-white border border-zinc-200/50 rounded-md items-center justify-center text-[7px] text-zinc-300 font-bold tracking-[0.25em] uppercase whitespace-nowrap overflow-hidden">
               HTTPS://APP.VELANK.AI
            </div>
            {/* Mobile Clock/Time simulation */}
            <div className="sm:hidden flex-1 text-center text-[10px] font-black text-zinc-400">9:41 AM</div>
          </div>
          
          <div className="flex-1 flex flex-col sm:flex-row overflow-hidden">
            {/* Elegant Sidebar - Hidden on mobile to focus on content */}
            <div className="hidden sm:flex w-[200px] bg-[#635BFF] flex-col pt-8 pb-6 shrink-0 relative overflow-hidden">
              <div className="absolute top-0 right-0 w-full h-full bg-gradient-to-br from-white/5 to-transparent pointer-events-none" />
              
              <div className="px-7 flex items-center gap-3 mb-12 relative z-10">
                <div className="w-8 h-8 rounded-lg bg-white/10 flex items-center justify-center border border-white/10 overflow-hidden p-1.5">
                  <div className="relative w-full h-full">
                    <Image src="/icon.svg" alt="Velank Icon" fill className="object-contain invert brightness-0" />
                  </div>
                </div>
                <span className="text-[19px] font-black text-white tracking-tighter">Velank AI</span>
              </div>
              
              <div className="flex-1 flex flex-col gap-1 px-3 relative z-10">
                {[
                  { label: "Dashboard", icon: LayoutDashboard, active: false },
                  { label: "LinkedIn Post", icon: Sparkles, active: false },
                  { label: "Scheduler", icon: Clock, active: false },
                  { label: "Database", icon: Database, active: true },
                  { label: "Settings", icon: Settings, active: false },
                ].map((item, i) => (
                  <div key={i} className={`px-5 py-2.5 rounded-[12px] text-[13px] font-black flex items-center gap-3.5 transition-all duration-300 group ${item.active ? 'bg-white/10 text-white shadow-lg ring-1 ring-white/10' : 'text-white/40 hover:text-white hover:bg-white/5'}`}>
                    <item.icon className={`w-[17px] h-[17px] transition-transform duration-300 ${item.active ? 'scale-110' : 'group-hover:scale-110'}`} /> 
                    {item.label}
                  </div>
                ))}
              </div>
              
              <div className="px-4 relative z-10">
                <div className="bg-white/5 border border-white/10 rounded-[20px] p-3.5 flex items-center gap-3.5 shadow-2xl backdrop-blur-md">
                  <div className="w-9 h-9 bg-white/20 rounded-xl flex items-center justify-center text-[11px] font-black text-white border border-white/20">U</div>
                  <div className="flex flex-col min-w-0">
                    <span className="text-[11px] font-black text-white truncate">User Account</span>
                    <span className="text-[9px] text-zinc-400 font-bold">Free Plan</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Main Content Area */}
            <div className="flex-1 bg-white p-4 sm:p-10 lg:p-12 flex flex-col overflow-hidden relative">
              <div className="absolute inset-0 bg-[radial-gradient(#e5e7eb_1px,transparent_1px)] [background-size:24px_24px] opacity-20 pointer-events-none" />
              
              <div className="flex flex-col sm:flex-row justify-between items-start mb-2 sm:mb-2 px-1 relative z-10 gap-1 sm:gap-4">
                <div className="flex flex-col gap-0.5">
                  <h2 className="text-[20px] sm:text-[28px] font-black text-[#111827] tracking-tight leading-none">Database</h2>
                  <p className="text-[10px] sm:text-[13px] text-zinc-400 font-medium leading-relaxed">
                    Manage your knowledge assets.
                  </p>
                </div>
                <div className="bg-[#FFF7ED] text-[#EA580C] border border-[#FFEDD5] px-2.5 py-1 rounded-full text-[8.5px] font-black flex items-center gap-1.5 shadow-sm shrink-0">
                  <div className="w-1 h-1 bg-[#EA580C] rounded-full animate-pulse shadow-[0_0_8px_rgba(234,88,12,0.5)]" />
                  48.7 MB USED
                </div>
              </div>
              
              {/* Internal Mobile Logo - Compacted */}
              <div className="sm:hidden flex items-center gap-1.5 mb-3 px-1 relative z-10 scale-90 origin-left">
                <div className="w-4.5 h-4.5 rounded bg-[#635BFF] flex items-center justify-center p-1">
                  <div className="relative w-full h-full">
                    <Image src="/icon.svg" alt="Icon" fill className="object-contain invert brightness-0" />
                  </div>
                </div>
                <span className="text-[11px] font-black text-[#635BFF] tracking-tighter">Velank AI</span>
              </div>
 
              {/* Status Tabs */}
              <div className="px-1 flex flex-wrap gap-1.5 sm:gap-2.5 my-2.5 sm:my-4 relative z-10">
                {[
                  { label: (step >= 3 ? '5 docs' : '4 docs'), dot: "bg-blue-500" },
                  { label: (step >= 6 ? '368 chks' : '344 chks'), dot: "bg-emerald-500" },
                  { label: "Healthy", dot: "bg-emerald-500" },
                ].map((chip, i) => (
                  <div key={i} className="bg-white border border-zinc-200 text-[8.5px] sm:text-[11px] px-2.5 sm:px-5 py-1 sm:py-2.5 rounded-full flex items-center gap-1.5 sm:gap-3 font-bold text-zinc-600 shadow-sm transition-all hover:border-zinc-300">
                    <div className={`w-1 h-1 sm:w-1.5 sm:h-1.5 rounded-full ${chip.dot} shadow-xl shrink-0`} />
                    <span className="shrink-0">{chip.label}</span>
                  </div>
                ))}
              </div>
 
              {/* Cards Row - Tightly packed for mobile, expanded for desktop */}
              <div className="flex flex-col sm:flex-row gap-3 sm:gap-6 flex-1 min-h-0 relative z-10 overflow-hidden pb-4">
                
                {/* Visual Step 1 Card */}
                <div className="w-full sm:flex-1 bg-[#635BFF] rounded-[20px] sm:rounded-[24px] p-4 sm:p-5 lg:p-6 text-white flex flex-col relative overflow-hidden shadow-2xl shadow-[#635BFF]/30 border border-white/5 group min-h-[150px] sm:min-h-[160px]">
                  <div className="bg-white/10 px-3 py-1 rounded-full w-max text-[8px] sm:text-[9px] font-black uppercase tracking-widest mb-2 border border-white/5 backdrop-blur-sm shrink-0">
                    Step 1 • Upload Files
                  </div>
                  <h3 className="text-[18px] sm:text-[20px] font-black mb-0.5 tracking-tight leading-none shrink-0">Add to Database</h3>
                  <p className="text-[9px] sm:text-[10px] text-white/70 font-medium mb-2 leading-relaxed shrink-0 flex items-center gap-1.5">
                    <CheckCircle2 className="w-2.5 h-2.5 opacity-50" />
                    Auto-indexed
                  </p>
                  
                  <div className={`flex-1 border-2 border-dashed rounded-[16px] sm:rounded-[20px] flex flex-col items-center justify-center transition-all duration-700 relative overflow-hidden bg-black/10 min-h-[55px] sm:min-h-[80px] ${step >= 2 ? 'border-white/60 bg-white/5' : 'border-white/20'}`}>
                    <AnimatePresence mode="wait">
                      {step <= 1 ? (
                        <motion.div key="up" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex flex-col items-center gap-1.5 w-full h-full justify-center p-1 relative">
                           <Inbox className="w-3.5 h-3.5 text-white/20" />
                           <p className="text-[9px] font-black uppercase tracking-wide">Drop files</p>
                           <div className="bg-white text-[#635BFF] px-3 py-1 rounded-lg text-[8px] font-black shadow-2xl mt-0.5">Choose File</div>
                           
                           {/* Simplified Mouse for Mobile */}
                           <motion.div initial={{ x: 60, y: 60 }} animate={step === 1 ? { x: 20, y: 10 } : { x: 60, y: 60 }} transition={{ duration: 1, ease: "easeInOut" }} className="absolute -bottom-2 -right-2 pointer-events-none z-[60] opacity-40">
                             <MousePointer2 className="w-5 h-5 text-zinc-900 fill-white" />
                           </motion.div>
                        </motion.div>
                      ) : step === 2 ? (
                        <motion.div key="upload" initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.95 }} className="flex flex-col justify-center w-full h-full px-5 sm:px-6 gap-2">
                           <div className="flex justify-between items-center text-[8px] sm:text-[10px] font-black tracking-[0.1em] text-white/90 uppercase mb-0.5">
                             <span>Processing...</span> 
                             <span className="font-mono">84%</span>
                           </div>
                           <div className="w-full bg-white/10 h-1.5 rounded-full overflow-hidden shrink-0 relative border border-white/5">
                             <motion.div initial={{ width: "0%" }} animate={{ width: "84%" }} transition={{ duration: 1.5 }} className="h-full bg-white shadow-[0_0_15px_white]" />
                           </div>
                        </motion.div>
                      ) : (
                        <motion.div key="done" initial={{ scale: 0.8, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} className="flex flex-col items-center justify-center gap-1.5 w-full h-full text-center">
                           <div className="w-8 h-8 sm:w-10 sm:h-10 bg-white rounded-lg sm:rounded-[14px] flex items-center justify-center shadow-xl border border-emerald-100/50">
                             <CheckCircle2 className="w-4.5 h-4.5 sm:w-6 sm:h-6 text-emerald-500" />
                           </div>
                           <span className="text-[9px] sm:text-[10px] font-black uppercase tracking-[0.2em] text-white w-full">Linked</span>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                </div>
                {/* Visual Step 2 Card */}
                <div className="w-full sm:flex-1 bg-white rounded-[20px] sm:rounded-[24px] p-4 sm:p-5 lg:p-6 border border-zinc-200 flex flex-col relative min-h-[145px] sm:min-h-[160px] shadow-sm group">
                   <div className="bg-[#EFEEFF] text-[#635BFF] px-3 py-1 rounded-full w-max text-[8px] sm:text-[10px] font-black uppercase tracking-widest mb-2 sm:mb-6 border border-[#635BFF]/5">
                    Step 2 • Training
                  </div>
                  
                  <span className="text-[9px] sm:text-[11px] font-black text-zinc-300 uppercase tracking-widest mb-0.5 shrink-0">Health Status</span>
                  <h3 className="text-[18px] sm:text-[20px] font-black text-[#111827] mb-2 sm:mb-4 tracking-tight leading-none shrink-0">
                     {step === 3 ? "Updating..." : "Ready"}
                  </h3>
                  
                  <div className={`flex items-center gap-1.5 sm:gap-3 px-3 sm:px-6 py-1.5 sm:py-3 rounded-[10px] sm:rounded-[16px] border transition-all duration-700 w-max mb-2 sm:mb-4 shrink-0 ${step >= 4 ? 'bg-[#ECFDF5] text-[#059669] border-[#D1FAE5]' : 'bg-zinc-50 border-zinc-100 text-zinc-300'}`}>
                    <CheckCircle2 className={`w-3 h-3 sm:w-4 sm:h-4 shrink-0 ${step >= 4 ? 'text-[#10B981]' : 'text-zinc-200'}`} />
                    <span className="text-[11px] sm:text-[13px] font-bold tracking-tight whitespace-nowrap shrink-0">Sync Done</span>
                  </div>
 
                  {/* BOTTOM STAT ROW - Cleaned for tight fit */}
                  <div className="grid grid-cols-3 gap-1.5 mt-auto">
                    {[
                      { val: '4', label: "IP", color: "text-blue-600" },
                      { val: step >= 6 ? '368' : '344', label: "CHKS", color: "text-emerald-600" },
                      { val: '4', label: "TRAIN", color: "text-orange-600" }
                    ].map((st, i) => (
                      <div key={i} className="bg-zinc-50/50 border border-zinc-100 rounded-[10px] py-1.5 flex flex-col items-center justify-center">
                        <span className={`text-[15px] sm:text-[20px] font-black mb-0 leading-none ${st.color}`}>
                          {st.val}
                        </span>
                        <span className="text-[6.5px] font-black text-zinc-400 tracking-wider uppercase">{st.label}</span>
                      </div>
                    ))}
                  </div>
                </div>

              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
};




