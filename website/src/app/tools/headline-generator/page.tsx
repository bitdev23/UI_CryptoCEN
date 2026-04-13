"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { Sparkles, Copy, Check, RefreshCw, Briefcase, Zap, Star } from "lucide-react";
import Link from 'next/link';
import { PoweredByVelank } from "@/components/ui/PoweredByVelank";

const MODES = [
  { id: "founder", label: "Founder", icon: <Zap className="w-4 h-4" />, color: "text-indigo-600", bg: "bg-indigo-50" },
  { id: "expert", label: "Thought Leader", icon: <Sparkles className="w-4 h-4" />, color: "text-emerald-600", bg: "bg-emerald-50" },
  { id: "executive", label: "Executive", icon: <Briefcase className="w-4 h-4" />, color: "text-amber-600", bg: "bg-amber-50" },
];

const TEMPLATES: Record<string, string[]> = {
  founder: [
    "Building {company} | Helping {audience} achieve {result} with AI",
    "Founder @ {company} | Scaling {audience} via {method} | {status}",
    "Obsessed with {niche} | Founder of {company} | {achievement}",
    "We help {audience} {result} without the {pain} | CEO @ {company}",
  ],
  expert: [
    "The {niche} Guy/Girl | Showing {audience} how to {result}",
    "Daily insights on {niche} | Helping {audience} stay ahead of {threat}",
    "Ex-{big_company} | Solving {pain} for {audience} through {method}",
    "Turning {problem} into {opportunity} for {audience} | {niche} Strategist",
  ],
  executive: [
    "VP of {niche} | Driving {result} at {company} | {achievement}",
    "Building the future of {niche} | Leadership @ {company}",
    "Scale & Strategy | Managing {metric} at {company} | {niche} Expert",
    "Empowering {audience} to {result} | {company} | Operations & Growth",
  ]
};

export default function HeadlineGenerator() {
  const [company, setCompany] = useState("");
  const [niche, setNiche] = useState("");
  const [audience, setAudience] = useState("");
  const [result, setResult] = useState("");
  const [mode, setMode] = useState("founder");
  const [generated, setGenerated] = useState<string[]>([]);
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);

  const generate = () => {
    const data: Record<string, string> = {
      company: company || "my startup",
      niche: niche || "AI strategy",
      audience: audience || "B2B founders",
      result: result || "10x growth",
      method: "proprietary frameworks",
      status: "Building in public",
      achievement: "Award-winning innovator",
      pain: "manual busywork",
      threat: "legacy inefficiency",
      problem: "stagnate growth",
      opportunity: "exponential scale",
      big_company: "Google",
      metric: "high-performance teams"
    };

    const templates = TEMPLATES[mode];
    const results = templates.map(t => {
      let head = t;
      Object.keys(data).forEach(key => {
        head = head.replace(new RegExp(`\\{${key}\\}`, "g"), data[key]);
      });
      return head;
    });
    setGenerated(results);
  };

  const copyToClipboard = (text: string, index: number) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  return (
    <div className="min-h-screen bg-white text-zinc-900 relative flex flex-col pt-28 font-sans">
      <Header />
      
      <main className="flex-1 container mx-auto px-6 py-20 max-w-4xl">
        <div className="text-center mb-16">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-50 border border-indigo-100 text-[10px] font-bold tracking-widest uppercase text-indigo-600 mb-6">
             Free Tool ✦ Alpha
          </div>
          <h1 className="text-4xl md:text-6xl font-black mb-6 tracking-tighter text-zinc-900">
            LinkedIn <span className="text-indigo-600">Headline</span> Generator.
          </h1>
          <p className="text-xl text-zinc-500 font-medium max-w-2xl mx-auto leading-relaxed">
            Stop sounding like a resume. Start sounding like an authority. Generate headlines that turn profile views into meetings.
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-12 bg-zinc-50 border border-zinc-200 rounded-[3rem] p-8 md:p-12 shadow-2xl relative overflow-hidden">
          <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-100 blur-[100px] pointer-events-none -translate-y-1/2 translate-x-1/2" />
          
          <div className="space-y-6 relative z-10">
            <div>
              <label className="block text-xs font-bold text-zinc-400 uppercase tracking-widest mb-2 ml-1">Your Identity</label>
              <div className="flex gap-2">
                {MODES.map((m) => (
                  <button
                    key={m.id}
                    onClick={() => setMode(m.id)}
                    className={`flex-1 flex items-center justify-center gap-2 py-3 rounded-xl text-xs font-bold transition-all border ${
                      mode === m.id 
                        ? `${m.bg} ${m.color} border-indigo-200 shadow-sm` 
                        : "bg-white text-zinc-400 border-zinc-200 hover:border-zinc-300"
                    }`}
                  >
                    {m.icon} {m.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-bold text-zinc-400 uppercase tracking-widest mb-2 ml-1">Company</label>
                <input 
                  type="text" value={company} onChange={(e) => setCompany(e.target.value)}
                  placeholder="e.g. Acme AI"
                  className="w-full bg-white border border-zinc-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 transition-all" 
                />
              </div>
              <div>
                <label className="block text-xs font-bold text-zinc-400 uppercase tracking-widest mb-2 ml-1">Niche</label>
                <input 
                  type="text" value={niche} onChange={(e) => setNiche(e.target.value)}
                  placeholder="e.g. Sales Ops"
                  className="w-full bg-white border border-zinc-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 transition-all" 
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-zinc-400 uppercase tracking-widest mb-2 ml-1">Who do you help?</label>
              <input 
                type="text" value={audience} onChange={(e) => setAudience(e.target.value)}
                placeholder="e.g. B2B Founders"
                className="w-full bg-white border border-zinc-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 transition-all" 
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-zinc-400 uppercase tracking-widest mb-2 ml-1">What is the result?</label>
              <input 
                type="text" value={result} onChange={(e) => setResult(e.target.value)}
                placeholder="e.g. double their pipeline"
                className="w-full bg-white border border-zinc-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 transition-all" 
              />
            </div>

            <button 
              onClick={generate}
              className="w-full bg-zinc-900 text-white rounded-2xl py-4 font-black text-lg hover:bg-zinc-800 transition-all shadow-xl active:scale-[0.98] flex items-center justify-center gap-3"
            >
              Generate Headlines <RefreshCw className="w-5 h-5" />
            </button>
          </div>

          <div className="bg-white border border-zinc-200 rounded-3xl p-6 shadow-inner flex flex-col h-full min-h-[400px]">
            <div className="text-[10px] font-bold text-zinc-400 uppercase tracking-[0.2em] mb-6 border-b border-zinc-100 pb-4">Generated Results</div>
            
            <div className="flex-1 space-y-4">
              <AnimatePresence mode="popLayout">
                {generated.length > 0 ? (
                  generated.map((headline, i) => (
                    <motion.div 
                      key={i}
                      initial={{ opacity: 0, x: 20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.1 }}
                      className="group p-4 bg-zinc-50 rounded-2xl border border-zinc-100 hover:border-indigo-200 transition-all relative"
                    >
                      <p className="text-sm font-bold text-zinc-800 pr-10 leading-relaxed">{headline}</p>
                      <button 
                        onClick={() => copyToClipboard(headline, i)}
                        className="absolute top-4 right-4 text-zinc-400 hover:text-indigo-600 transition-colors"
                      >
                        {copiedIndex === i ? <Check className="w-5 h-5 text-emerald-500" /> : <Copy className="w-5 h-5" />}
                      </button>
                    </motion.div>
                  ))
                ) : (
                  <div className="h-full flex flex-col items-center justify-center text-center opacity-30 px-6">
                    <Star className="w-12 h-12 mb-4 text-zinc-300" />
                    <p className="text-sm font-bold">Fill out the form to generate authority headlines.</p>
                  </div>
                )}
              </AnimatePresence>
            </div>

              <PoweredByVelank />
            </div>
          </div>
        </main>

        <Footer />
      </div>
    );
  }
