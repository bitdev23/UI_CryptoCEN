"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { Search, Copy, Check, Sparkles, TrendingUp, AlertCircle } from "lucide-react";
import Link from "next/link";
import { PoweredByVelank } from "@/components/ui/PoweredByVelank";

const CATEGORIES = [
  { id: "all", label: "All Hooks" },
  { id: "contrarian", label: "The Contrarian", description: "Challenge the status quo." },
  { id: "result", label: "The Result", description: "Showcase big wins." },
  { id: "mistake", label: "The Mistake", description: "Share lessons learned." },
  { id: "system", label: "The System", description: "Break down your process." },
];

const HOOKS = [
  { id: 1, cat: "contrarian", text: "Most people think {niche} is about X. It's actually about Y.", usage: "High Engagement" },
  { id: 2, cat: "result", text: "I generated {result} in just {time}. Here is the exact breakdown.", usage: "High Conversion" },
  { id: 3, cat: "mistake", text: "I spent {time} doing {action}. It was a waste of time. Here's what I do now.", usage: "High Trust" },
  { id: 4, cat: "system", text: "My 3-step system for achieving {result} (without the {pain}).", usage: "High Save Rate" },
  { id: 5, cat: "contrarian", text: "Stop doing {action}. It's killing your {metric}.", usage: "High Click-through" },
  { id: 6, cat: "result", text: "The brutal truth about {niche}: {result} is not an accident.", usage: "Viral Potential" },
  { id: 7, cat: "system", text: "If I had to start from zero in {niche}, this is exactly what I would do.", usage: "High Authority" },
  { id: 8, cat: "mistake", text: "The biggest mistake {audience} make when {action}.", usage: "Educational" },
];

export default function HookVault() {
  const [activeCat, setActiveCat] = useState("all");
  const [search, setSearch] = useState("");
  const [copiedId, setCopiedId] = useState<number | null>(null);

  const filtered = HOOKS.filter(h => {
    const matchesCat = activeCat === "all" || h.cat === activeCat;
    const matchesSearch = h.text.toLowerCase().includes(search.toLowerCase());
    return matchesCat && matchesSearch;
  });

  const copyToClipboard = (text: string, id: number) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className="min-h-screen bg-white text-zinc-900 relative flex flex-col pt-28 font-sans">
      <Header />
      
      <main className="flex-1 container mx-auto px-6 py-20 max-w-6xl">
        <div className="text-center mb-16">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-50 border border-indigo-100 text-[10px] font-bold tracking-widest uppercase text-indigo-600 mb-6">
             Content Strategy ✦ Free
          </div>
          <h1 className="text-4xl md:text-6xl font-black mb-6 tracking-tighter text-zinc-900">
            The LinkedIn <span className="text-indigo-600">Hook</span> Vault.
          </h1>
          <p className="text-xl text-zinc-500 font-medium max-w-2xl mx-auto leading-relaxed">
            Stop staring at a blank screen. Access our curated library of 50+ high-performing LinkedIn hooks that stop the scroll.
          </p>
        </div>

        <div className="flex flex-col lg:flex-row gap-12">
          {/* Sidebar Filters */}
          <div className="lg:w-1/4 space-y-8">
            <div className="relative">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400" />
              <input 
                type="text" 
                placeholder="Search hooks..." 
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full bg-zinc-50 border border-zinc-200 rounded-2xl pl-11 pr-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 transition-all font-medium"
              />
            </div>

            <div>
              <h3 className="text-xs font-bold text-zinc-400 uppercase tracking-widest mb-4 ml-1">Categories</h3>
              <div className="space-y-2">
                {CATEGORIES.map((cat) => (
                  <button
                    key={cat.id}
                    onClick={() => setActiveCat(cat.id)}
                    className={`w-full text-left px-4 py-3 rounded-xl text-sm font-bold transition-all border ${
                      activeCat === cat.id 
                        ? "bg-indigo-600 text-white border-indigo-600 shadow-lg shadow-indigo-100" 
                        : "bg-white text-zinc-500 border-zinc-100 hover:border-zinc-200"
                    }`}
                  >
                    {cat.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="p-6 bg-zinc-900 rounded-[2rem] text-white overflow-hidden relative group">
               <div className="absolute top-0 right-0 w-32 h-32 bg-indigo-500/20 blur-2xl rounded-full" />
               <p className="text-xs font-bold text-indigo-300 uppercase tracking-widest mb-3 relative z-10">Pro Version</p>
               <h4 className="text-xl font-bold mb-4 relative z-10 leading-tight">Get 500+ daily AI hooks tailored to your niche.</h4>
               <Link href="/pricing" className="inline-flex items-center gap-2 text-sm font-black text-white hover:text-indigo-300 transition-colors relative z-10 group-hover:gap-3">
                 Upgrade to Pro <TrendingUp className="w-4 h-4" />
               </Link>
            </div>
          </div>

          {/* Hooks Grid */}
          <div className="lg:w-3/4">
            <div className="grid md:grid-cols-2 gap-6">
              <AnimatePresence mode="popLayout">
                {filtered.map((hook) => (
                  <motion.div 
                    key={hook.id}
                    layout
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.9 }}
                    className="p-6 bg-white border border-zinc-200 rounded-3xl hover:border-indigo-300 transition-all shadow-sm hover:shadow-xl hover:shadow-indigo-500/5 group flex flex-col justify-between"
                  >
                    <div>
                        <div className="flex justify-between items-start mb-4">
                           <span className="text-[10px] font-black uppercase tracking-widest px-2 py-1 bg-zinc-100 rounded-md text-zinc-500">
                             {hook.cat}
                           </span>
                           <button 
                             onClick={() => copyToClipboard(hook.text, hook.id)}
                             className="text-zinc-300 hover:text-indigo-600 transition-colors"
                           >
                             {copiedId === hook.id ? <Check className="w-5 h-5 text-emerald-500" /> : <Copy className="w-5 h-5" />}
                           </button>
                        </div>
                        <p className="text-lg font-bold text-zinc-800 leading-snug mb-6">{hook.text}</p>
                    </div>
                    <div className="flex items-center gap-2 text-[10px] font-bold text-emerald-600 uppercase tracking-widest">
                       <Sparkles className="w-3 h-3" /> {hook.usage}
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>

            {filtered.length === 0 && (
              <div className="text-center py-20 bg-zinc-50 rounded-[3rem] border border-dashed border-zinc-200">
                 <AlertCircle className="w-12 h-12 text-zinc-300 mx-auto mb-4" />
                 <p className="text-zinc-500 font-bold">No hooks found matching your search.</p>
              </div>
            )}
          </div>
        </div>
        
        <div className="mt-16 bg-white border border-zinc-200 rounded-[3rem] p-8 shadow-sm">
           <PoweredByVelank />
        </div>
      </main>

      <Footer />
    </div>
  );
}
