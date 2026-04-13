"use client";

import { useState } from "react";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { motion, AnimatePresence } from "framer-motion";
import { Sparkles, MessageSquare, Target, UserPlus, CheckCircle2, Info, Copy, Check } from "lucide-react";
import Link from "next/link";
import { PoweredByVelank } from "@/components/ui/PoweredByVelank";

const personaStyles = [
  { id: "contrarian", name: "The Contrarian", icon: Target, color: "text-red-500", bg: "bg-red-50", border: "border-red-100" },
  { id: "visionary", name: "The Visionary", icon: Sparkles, color: "text-indigo-500", bg: "bg-indigo-50", border: "border-indigo-100" },
  { id: "expert", name: "The Expert", icon: CheckCircle2, color: "text-emerald-500", bg: "bg-emerald-50", border: "border-emerald-100" },
];

export default function GhostTester() {
  const [postContent, setPostContent] = useState("");
  const [activeStyle, setActiveStyle] = useState(personaStyles[1].id);
  const [isGenerating, setIsGenerating] = useState(false);
  const [comment, setComment] = useState("");
  const [copied, setCopied] = useState(false);

  const generateComment = () => {
    if (!postContent) return;
    setIsGenerating(true);
    setComment("");
    
    setTimeout(() => {
      let result = "";
      const leadPoint = postContent.slice(0, 30) + "...";
      
      if (activeStyle === "contrarian") {
        result = `I actually see it differently. While ${leadPoint} is a common take, we've found that the inverse is often more effective for high-ticket sales. The key is in inverted curiosity—not just standard engagement.`;
      } else if (activeStyle === "visionary") {
        result = `Spot on. This aligns perfectly with the 'Authority First' framework we use at Velank AI. Posting is only 20% of the work; it's these deep insights that build the real trust.`;
      } else {
        result = `The data confirms this. Our internal benchmarking across 20k+ profiles shows that when you bridge ${leadPoint} with a clear technical insight, inbound leads increase by an average of 42%.`;
      }
      
      setComment(result);
      setIsGenerating(false);
    }, 1500);
  };

  const copyToClipboard = () => {
    navigator.clipboard.writeText(comment);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="min-h-screen bg-zinc-50 text-zinc-900 font-sans selection:bg-indigo-100 selection:text-indigo-900">
      <Header />
      
      <main className="pt-32 pb-20">
        <div className="container mx-auto px-6 max-w-4xl">
          <div className="text-center mb-16">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-50 border border-indigo-100 text-[10px] font-bold tracking-[0.2em] uppercase text-indigo-600 mb-6 shadow-sm">
              <MessageSquare className="w-3.5 h-3.5" /> Ghost AI Engine
            </div>
            <h1 className="text-4xl md:text-6xl font-black tracking-tighter mb-6 text-zinc-900 leading-tight">
              Test your <span className="text-indigo-600 italic font-serif">Digital Twin.</span>
            </h1>
            <p className="text-lg text-zinc-500 font-medium max-w-2xl mx-auto">
              Paste a lead&apos;s post below and see how your AI persona would comment to build a relationship—without sounding like a bot.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-start">
            {/* Input Side */}
            <div className="bg-white rounded-[2.5rem] p-8 shadow-2xl shadow-zinc-200 border border-zinc-100 flex flex-col">
              <div className="flex items-center gap-2 mb-4 text-zinc-400">
                <Info className="w-4 h-4" />
                <span className="text-[10px] font-bold uppercase tracking-widest">Post Content</span>
              </div>
              <textarea 
                className="w-full h-48 bg-zinc-50 rounded-2xl p-6 text-sm font-medium text-zinc-800 placeholder:text-zinc-300 outline-none border border-transparent focus:border-indigo-100 transition-all resize-none mb-8"
                placeholder="Paste the LinkedIn post here..."
                value={postContent}
                onChange={(e) => setPostContent(e.target.value)}
              />

              <div className="mb-8">
                <div className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-4">Choose Your Voice</div>
                <div className="flex flex-wrap gap-2">
                  {personaStyles.map((style) => (
                    <button
                      key={style.id}
                      onClick={() => setActiveStyle(style.id)}
                      className={`flex items-center gap-2 px-4 py-2.5 rounded-xl border-2 transition-all font-bold text-sm ${
                        activeStyle === style.id 
                        ? `${style.border} ${style.bg} ${style.color} scale-105 shadow-sm` 
                        : "border-transparent bg-zinc-50 text-zinc-400 hover:bg-zinc-100"
                      }`}
                    >
                      <style.icon className="w-4 h-4" />
                      {style.name}
                    </button>
                  ))}
                </div>
              </div>

              <button 
                onClick={generateComment}
                disabled={isGenerating || !postContent}
                className="w-full py-4 bg-indigo-600 text-white rounded-2xl font-black text-lg shadow-xl shadow-indigo-600/20 hover:bg-indigo-700 active:scale-95 transition-all flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed group"
              >
                {isGenerating ? "Analyzing Character..." : "Draft Comment"} <Sparkles className={`w-5 h-5 ${isGenerating ? 'animate-spin' : 'group-hover:scale-125 transition-transform'}`} />
              </button>
            </div>

            {/* Output Side */}
            <div className="bg-white rounded-[2.5rem] p-8 shadow-2xl shadow-zinc-200 border border-zinc-100 flex flex-col min-h-[400px] relative overflow-hidden">
               <div className="absolute top-0 right-0 px-4 py-2 bg-indigo-50 text-indigo-600 border-bl border-indigo-100 text-[10px] font-black uppercase tracking-widest rounded-bl-2xl">
                 Velank Output
               </div>

               <div className="mb-8">
                 <div className="flex items-center gap-3 mb-6">
                    <div className="w-10 h-10 rounded-full bg-indigo-600 flex items-center justify-center text-white font-black text-lg">V</div>
                    <div>
                      <div className="text-sm font-bold text-zinc-900">Your AI Persona</div>
                      <div className="text-[10px] text-zinc-400 font-bold uppercase tracking-widest">Active • Ready to publish</div>
                    </div>
                 </div>

                 <AnimatePresence mode="wait">
                   {isGenerating ? (
                     <motion.div 
                       key="loading"
                       initial={{ opacity: 0 }}
                       animate={{ opacity: 1 }}
                       exit={{ opacity: 0 }}
                       className="space-y-4 py-4"
                     >
                       <div className="h-4 w-full bg-zinc-100 rounded-full animate-pulse" />
                       <div className="h-4 w-[85%] bg-zinc-100 rounded-full animate-pulse" />
                       <div className="h-4 w-[95%] bg-zinc-100 rounded-full animate-pulse" />
                     </motion.div>
                   ) : comment ? (
                     <motion.div 
                       key="result"
                       initial={{ opacity: 0, y: 10 }}
                       animate={{ opacity: 1, y: 0 }}
                       className="relative"
                     >
                       <p className="text-lg text-zinc-700 leading-relaxed font-semibold italic border-l-4 border-indigo-100 pl-6 py-2">
                         &quot;{comment}&quot;
                       </p>
                       <button 
                        onClick={copyToClipboard}
                        className="absolute -right-2 -bottom-12 p-3 bg-zinc-50 rounded-xl hover:bg-zinc-100 text-zinc-400 hover:text-indigo-600 transition-all flex items-center gap-2 font-bold text-xs"
                       >
                         {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                         {copied ? "Copied!" : "Copy to LinkedIn"}
                       </button>
                     </motion.div>
                   ) : (
                     <div className="py-20 flex flex-col items-center justify-center text-center">
                       <MessageSquare className="w-12 h-12 text-zinc-100 mb-4" />
                       <p className="text-sm font-bold text-zinc-300">Enter post content and <br/> choose a voice to start.</p>
                     </div>
                   )}
                 </AnimatePresence>
               </div>

               <PoweredByVelank />

               {/* Simulation Footer */}
               <div className="mt-auto py-6 border-t border-zinc-100 flex flex-col gap-6">
                  <div className="p-4 bg-indigo-50/50 rounded-2xl border border-indigo-100 flex items-center gap-4">
                    <UserPlus className="w-6 h-6 text-indigo-600 shrink-0" />
                    <div>
                      <div className="text-xs font-black text-indigo-900 uppercase tracking-wide">Ghost Engagement Pro</div>
                      <p className="text-[10px] text-indigo-600/80 font-bold">Automate this for 50 leads/day with your custom Digital Twin.</p>
                    </div>
                  </div>
                  <Link href="/pricing" className="w-full py-4 bg-indigo-600 text-white rounded-2xl font-black text-center shadow-lg active:scale-95 transition-all">
                     Unlock Full Automation
                  </Link>
               </div>
            </div>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}
