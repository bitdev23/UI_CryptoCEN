import { useState } from "react";
import { X } from "lucide-react";
import Link from "next/link";
import { CountdownTimer } from "./CountdownTimer";
 
export function TopBanner() {
  const [isVisible, setIsVisible] = useState(true);
 
  if (!isVisible) return null;
 
  return (
    <div className="w-full bg-indigo-600 text-white flex items-center justify-center text-[10px] sm:text-xs font-bold relative z-[100] py-2.5 overflow-hidden border-b border-white/10 uppercase tracking-tighter group transition-colors">
      <div className="w-full flex items-center justify-center gap-2 sm:gap-4 px-4 sm:px-10 text-center overflow-hidden">
        <div className="flex items-center gap-1.5 shrink-0">
          <span className="shrink-0 animate-bounce">🔥</span>
          <span className="whitespace-nowrap uppercase">30% OFF</span>
          <span className="hidden xs:inline uppercase whitespace-nowrap">ALL PLANS</span>
        </div>
        <span className="hidden md:inline mx-1 opacity-20 shrink-0">|</span>
        <div className="hidden sm:block">
          <CountdownTimer />
        </div>
        <span className="hidden sm:inline mx-1 opacity-20 shrink-0">|</span>
        <Link href="/pricing" className="underline whitespace-nowrap text-white hover:text-indigo-100 transition-colors shrink-0">CLAIM OFFER &rarr;</Link>
      </div>
      <button onClick={() => setIsVisible(false)} className="absolute right-2 top-1/2 -translate-y-1/2 text-white/40 hover:text-white p-1 transition-colors">
        <X className="w-4 h-4" />
      </button>
    </div>
  );
}
