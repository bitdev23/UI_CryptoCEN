"use client";

import { useState } from "react";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { motion, AnimatePresence } from "framer-motion";
import { Sparkles, ArrowRight, CheckCircle2, Trophy, AlertTriangle, Target, TrendingUp, Mail } from "lucide-react";
import Link from "next/link";
import { PoweredByVelank } from "@/components/ui/PoweredByVelank";

const questions = [
  {
    id: 1,
    text: "How often do you currently post on LinkedIn?",
    options: [
      { text: "Every single day (5-7x/week)", score: 20 },
      { text: "Consistency (3x/week)", score: 15 },
      { text: "Occasionally (1x/week)", score: 10 },
      { text: "Rarely/Never", score: 5 }
    ]
  },
  {
    id: 2,
    text: "What is your primary goal for your personal brand?",
    options: [
      { text: "Generating High-Ticket Inbound Leads", score: 20 },
      { text: "Building Industry Thought Leadership", score: 15 },
      { text: "Recruiting & Talent Attraction", score: 10 },
      { text: "Networking & General Visibility", score: 5 }
    ]
  },
  {
    id: 3,
    text: "Is your Profile & Banner optimized for conversion?",
    options: [
      { text: "Yes, it's a funnel for my offer", score: 20 },
      { text: "It looks professional, but could be better", score: 10 },
      { text: "It's mostly just an online resume", score: 5 }
    ]
  },
  {
    id: 4,
    text: "How do you handle incoming comments and DMs?",
    options: [
      { text: "I have a systematic nurture process", score: 20 },
      { text: "I try to respond manually when I have time", score: 10 },
      { text: "I rarely engage with my audience", score: 5 }
    ]
  },
  {
    id: 5,
    text: "Do you use AI to ground your posts in your actual expertise?",
    options: [
      { text: "Yes, I use a Digital Twin with my knowledge", score: 20 },
      { text: "I use generic AI (ChatGPT) for drafts", score: 10 },
      { text: "I write everything manually from scratch", score: 5 }
    ]
  }
];

export default function AuthorityQuiz() {
  const [step, setStep] = useState(0); // 0: Start, 1-5: Questions, 6: Calculating, 7: Result
  const [score, setScore] = useState(0);
  const [email, setEmail] = useState("");

  const handleAnswer = (points: number) => {
    setScore(score + points);
    if (step < questions.length) {
      setStep(step + 1);
    } else {
      setStep(6);
      setTimeout(() => setStep(7), 2000);
    }
  };

  const getStatus = (s: number) => {
    if (s >= 85) return { label: "Elite Authority", color: "text-emerald-500", icon: Trophy, desc: "You are in the top 1% of creators. Your strategy is solid, but Velank can help you scale to multiple profiles." };
    if (s >= 65) return { label: "Growing Brand", color: "text-indigo-500", icon: TrendingUp, desc: "You have the foundation, but your conversion gaps are leaking leads. You need a systematic Digital Twin." };
    return { label: "Invisibility Risk", color: "text-red-500", icon: AlertTriangle, desc: "Your presence is inconsistent and missing critical conversion hooks. You are working too hard for too little ROI." };
  };

  const resultStatus = getStatus(score);

  return (
    <div className="min-h-screen bg-zinc-50 text-zinc-900 font-sans selection:bg-indigo-100 italic selection:text-indigo-900">
      <Header />
      
      <main className="pt-32 pb-20">
        <div className="container mx-auto px-6 max-w-3xl">
          <AnimatePresence mode="wait">
            {step === 0 && (
              <motion.div
                key="start"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                className="text-center py-20 bg-white rounded-[3rem] p-12 shadow-2xl shadow-zinc-200 border border-zinc-100"
              >
                <div className="w-16 h-16 bg-indigo-50 rounded-2xl flex items-center justify-center mx-auto mb-8 border border-indigo-100">
                   <Target className="w-8 h-8 text-indigo-600" />
                </div>
                <h1 className="text-4xl md:text-6xl font-black tracking-tighter mb-6 text-zinc-900 leading-tight">
                  What is your <span className="text-indigo-600 italic font-serif">Authority Score?</span>
                </h1>
                <p className="text-xl text-zinc-500 font-medium mb-12 max-w-lg mx-auto leading-relaxed">
                  Take the 60-second audit to see where your LinkedIn strategy is failing and how to fix it in 2026.
                </p>
                <button
                  onClick={() => setStep(1)}
                  className="px-12 py-5 bg-indigo-600 text-white rounded-2xl font-black text-xl shadow-xl shadow-indigo-600/20 hover:bg-indigo-700 active:scale-95 transition-all group"
                >
                  Start The Audit <ArrowRight className="ml-2 w-5 h-5 inline group-hover:translate-x-1 transition-transform" />
                </button>
              </motion.div>
            )}

            {step >= 1 && step <= 5 && (
              <motion.div
                key={`q-${step}`}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                className="bg-white rounded-[3rem] p-12 shadow-2xl shadow-zinc-200 border border-zinc-100"
              >
                <div className="flex justify-between items-center mb-12">
                   <div className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest">Question {step} / 5</div>
                   <div className="h-2 w-32 bg-zinc-100 rounded-full overflow-hidden">
                      <div className="h-full bg-indigo-500 transition-all duration-500" style={{ width: `${(step / 5) * 100}%` }} />
                   </div>
                </div>
                
                <h2 className="text-3xl font-black text-zinc-900 mb-10 tracking-tight">
                  {questions[step - 1].text}
                </h2>

                <div className="space-y-4">
                  {questions[step - 1].options.map((opt, i) => (
                    <button
                      key={i}
                      onClick={() => handleAnswer(opt.score)}
                      className="w-full text-left p-6 rounded-2xl border-2 border-zinc-100 hover:border-indigo-500 hover:bg-indigo-50 transition-all font-bold text-lg group flex items-center justify-between"
                    >
                      {opt.text}
                      <ArrowRight className="w-5 h-5 opacity-0 group-hover:opacity-100 transition-opacity text-indigo-500" />
                    </button>
                  ))}
                </div>
              </motion.div>
            )}

            {step === 6 && (
              <motion.div
                key="loading"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="text-center py-32"
              >
                <div className="relative w-24 h-24 mx-auto mb-8">
                   <div className="absolute inset-0 border-4 border-indigo-100 rounded-full" />
                   <div className="absolute inset-0 border-4 border-indigo-600 rounded-full border-t-transparent animate-spin" />
                </div>
                <h3 className="text-2xl font-black text-zinc-900 mb-2">Calculating Your Rank...</h3>
                <p className="text-zinc-400 font-bold uppercase tracking-widest text-xs">Analyzing Benchmarks</p>
              </motion.div>
            )}

            {step === 7 && (
              <motion.div
                key="result"
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="bg-white rounded-[3rem] p-12 shadow-2xl shadow-zinc-200 border border-zinc-100 text-center"
              >
                <div className="w-20 h-20 bg-indigo-50 rounded-full flex items-center justify-center mx-auto mb-8">
                   <resultStatus.icon className={`w-10 h-10 ${resultStatus.color}`} />
                </div>
                <div className="text-[10px] font-bold text-zinc-400 uppercase tracking-[0.3em] mb-4">Your Authority Score</div>
                <div className="text-8xl font-black text-zinc-900 tracking-tighter mb-4">{score}<span className="text-3xl text-zinc-300">/100</span></div>
                
                <div className={`text-xl font-black ${resultStatus.color} uppercase tracking-widest mb-8`}>
                   {resultStatus.label}
                </div>

                <div className="p-8 bg-zinc-50 rounded-[2rem] border border-zinc-100 mb-12 text-zinc-600 font-medium leading-relaxed italic">
                   &quot;{resultStatus.desc}&quot;
                </div>

                {/* Email Capture Hook */}
                <div className="max-w-md mx-auto">
                    <h4 className="text-lg font-black text-zinc-900 mb-4">Get the full 12-page breakdown.</h4>
                    <p className="text-sm text-zinc-500 mb-8 font-medium">We analyzed your responses against 20k top creators. Where do you want us to send your deep-dive PDF?</p>
                    
                    <div className="flex flex-col gap-4">
                       <div className="relative">
                          <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-zinc-400" />
                          <input 
                            type="email" 
                            placeholder="your@email.com" 
                            className="w-full h-14 pl-12 pr-6 rounded-2xl border border-zinc-200 focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/10 outline-none transition-all font-bold"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                          />
                       </div>
                       <button className="h-14 bg-indigo-600 text-white rounded-2xl font-black text-lg shadow-xl hover:bg-indigo-700 transition-all flex items-center justify-center gap-2">
                          Send Detailed Report <Sparkles className="w-5 h-5" />
                       </button>
                    </div>
                </div>

                <div className="mt-8 pt-8 border-t border-zinc-100">
                   <PoweredByVelank />
                </div>

                <div className="mt-12 pt-8 border-t border-zinc-100">
                    <Link href="/pricing" className="text-indigo-600 font-bold hover:underline">
                      Skip report and see how Velank AI scales your score &rarr;
                    </Link>
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
