"use client";

import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Sparkles, ArrowRight, ShieldCheck, Zap } from "lucide-react";
import Link from "next/link";
import { MagneticButton } from "./MagneticButton";

export function ExitIntent() {
  const [isVisible, setIsVisible] = useState(false);
  const [hasShown, setHasShown] = useState(false);

  useEffect(() => {
    // Check if user has already seen it in this session
    const shown = sessionStorage.getItem("exit_popup_shown_v2");
    if (shown) {
      setHasShown(true);
      return;
    }

    const handleMouseLeave = (e: MouseEvent) => {
      // Trigger if mouse leaves the top of the window
      if (e.clientY <= 5 && !hasShown) {
        setIsVisible(true);
        setHasShown(true);
        sessionStorage.setItem("exit_popup_shown_v2", "true");
      }
    };

    document.addEventListener("mouseleave", handleMouseLeave);
    return () => document.removeEventListener("mouseleave", handleMouseLeave);
  }, [hasShown]);

  const closePopup = () => setIsVisible(false);

  return (
    <AnimatePresence>
      {isVisible && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-6 bg-zinc-900/60 backdrop-blur-md">
          <motion.div
            initial={{ opacity: 0, scale: 0.9, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9, y: 10 }}
            className="bg-white rounded-[3rem] w-full max-w-2xl overflow-hidden shadow-[0_50px_100px_rgba(0,0,0,0.4)] relative border border-zinc-200"
          >
            {/* Background elements */}
            <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-50 rounded-full blur-[80px] -translate-y-1/2 translate-x-1/2 opacity-50" />
            <div className="absolute bottom-0 left-0 w-48 h-48 bg-emerald-50 rounded-full blur-[60px] translate-y-1/2 -translate-x-1/2 opacity-50" />

            <button
              onClick={closePopup}
              className="absolute top-6 right-6 p-2 rounded-full hover:bg-zinc-100 transition-colors z-20 text-zinc-400 hover:text-zinc-900"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="flex flex-col md:flex-row h-full relative z-10">
              {/* Left Side: Visual/Offer */}
              <div className="md:w-2/5 bg-zinc-900 p-8 md:p-12 text-white flex flex-col justify-between relative overflow-hidden group min-h-[300px] md:min-h-auto">
                <div className="absolute inset-0 bg-brand-mesh opacity-20 group-hover:opacity-30 transition-opacity" />
                <div className="relative z-10">
                  <div className="w-12 h-12 bg-white/10 rounded-2xl flex items-center justify-center mb-8 border border-white/20">
                    <ShieldCheck className="w-6 h-6 text-indigo-400" />
                  </div>
                  <h3 className="text-3xl font-black mb-4 leading-tight italic tracking-tighter">Wait!</h3>
                  <p className="text-zinc-400 text-sm font-medium leading-relaxed">
                    Don&apos;t leave without your <span className="text-white font-bold">Authority Score.</span>
                  </p>
                </div>
                <div className="mt-12 relative z-10">
                  <div className="flex -space-x-3 mb-4">
                    {[1, 2, 3].map(i => (
                      <div key={i} className="w-10 h-10 rounded-full bg-zinc-800 border-2 border-zinc-900 flex items-center justify-center text-[10px] font-black">
                        {i === 1 ? "JD" : i === 2 ? "MK" : "SL"}
                      </div>
                    ))}
                    <div className="w-10 h-10 rounded-full bg-indigo-600 border-2 border-zinc-900 flex items-center justify-center text-[8px] font-black underline">
                      +12k
                    </div>
                  </div>
                  <p className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest italic">Join 12,000+ B2B leaders</p>
                </div>
              </div>

              {/* Right Side: Content/CTA */}
              <div className="md:w-3/5 p-8 md:p-12 flex flex-col justify-center text-zinc-900">
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-50 border border-emerald-100 text-[10px] font-bold tracking-widest uppercase text-emerald-600 mb-6 shadow-sm">
                  <Sparkles className="w-3.5 h-3.5" /> High-Value Gift
                </div>
                <h4 className="text-2xl font-extrabold mb-6 tracking-tight leading-tight">
                  Claim Your Free <span className="text-indigo-600 italic">Audit</span> <br /> & 30% Limited Discount.
                </h4>
                <p className="text-zinc-500 mb-8 font-medium text-sm leading-relaxed">
                  Get a hard-hitting, 12-point authority audit (usually $19) for FREE + lock in a <span className="text-zinc-900 font-bold">30% discount</span> on any plan.
                </p>

                <div className="space-y-4">
                  <MagneticButton>
                    <Link
                      href="/audit"
                      onClick={closePopup}
                      className="w-full inline-flex items-center justify-center gap-2 px-6 py-4 bg-zinc-900 text-white rounded-2xl font-black text-sm shadow-xl hover:bg-black transition-all group"
                    >
                      Audit My Profile & Claim 30% <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                    </Link>
                  </MagneticButton>
                  <button
                    onClick={closePopup}
                    className="w-full py-2 text-zinc-400 hover:text-zinc-600 font-bold text-xs uppercase tracking-widest transition-colors"
                  >
                    No thanks, I choose to stay quiet
                  </button>
                </div>

                <div className="mt-10 pt-8 border-t border-zinc-100 flex items-center gap-3">
                   <div className="w-8 h-8 rounded-lg bg-emerald-50 flex items-center justify-center border border-emerald-100">
                     <Zap className="w-4 h-4 text-emerald-600" />
                   </div>
                   <p className="text-[10px] font-bold text-emerald-700 leading-tight">
                      Free forever access • Takes 60 seconds • Instant ROI
                   </p>
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
