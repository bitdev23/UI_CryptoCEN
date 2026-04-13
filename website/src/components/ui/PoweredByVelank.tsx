"use client";

import Link from "next/link";
import { Sparkles } from "lucide-react";

export function PoweredByVelank() {
  return (
    <div className="mt-8 pt-6 border-t border-zinc-100 flex items-center justify-between">
      <Link 
        href="/" 
        className="flex items-center gap-2 group"
      >
        <div className="w-6 h-6 rounded-lg bg-indigo-600 flex items-center justify-center text-white text-[10px] font-black group-hover:scale-110 transition-transform">V</div>
        <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest group-hover:text-indigo-600 transition-colors">
          Powered by <span className="text-zinc-900">Velank AI</span>
        </span>
      </Link>
      <Link 
        href="/pricing" 
        className="text-[10px] font-black text-indigo-600 uppercase tracking-widest hover:underline flex items-center gap-1"
      >
        Get 30% Off <Sparkles className="w-3 h-3" />
      </Link>
    </div>
  );
}
