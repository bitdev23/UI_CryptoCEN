"use client";

import { useState } from "react";
import { TrendingUp, Clock, Zap, Calculator } from "lucide-react";

export function RevenueCalculator({ symbol = "$" }: { symbol?: string }) {
  const [dealValue, setDealValue] = useState(5000);
  const [postsPerWeek, setPostsPerWeek] = useState(3);
  const [hourlyRate, setHourlyRate] = useState(150);
  
  const hoursSavedYearly = Math.round(postsPerWeek * 2.5 * 52); // Assumes 2.5 hours per post manually
  const timeValueSaved = hoursSavedYearly * hourlyRate;
  
  // Typical Velank users see a 2.4x increase in inbound, but we'll be conservative
  // Assume 1 extra deal per quarter due to consistent authority
  const conservativeRevenueIncrease = dealValue * 4; 
  const totalROI = timeValueSaved + conservativeRevenueIncrease;

  return (
    <div className="bg-white border-2 border-indigo-100 rounded-[3rem] p-8 md:p-12 shadow-2xl relative overflow-hidden group">
      <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-50 blur-[100px] pointer-events-none -translate-y-1/2 translate-x-1/2" />
      
      <div className="flex flex-col lg:flex-row gap-12 relative z-10">
        <div className="lg:w-1/2">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-50 border border-indigo-100 text-[10px] font-bold tracking-widest uppercase text-indigo-600 mb-6">
            <Calculator className="w-3.5 h-3.5" /> ROI Estimator
          </div>
          <h3 className="text-3xl md:text-4xl font-black text-zinc-900 mb-6 tracking-tight">
            Calculate your <br/> <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-600 to-[#8C7BFF]">Authority ROI.</span>
          </h3>
          <p className="text-zinc-500 font-medium mb-10 leading-relaxed">
            See how much your time is worth when you automate your consistency. Velank AI pays for itself in weeks, not months.
          </p>

          <div className="space-y-8">
            <div>
              <div className="flex justify-between mb-4">
                <span className="text-sm font-bold text-zinc-700">Average Deal Value</span>
                <span className="text-sm font-black text-indigo-600">{symbol}{dealValue.toLocaleString()}</span>
              </div>
              <input 
                type="range" min="1000" max="50000" step="1000" 
                value={dealValue} onChange={(e) => setDealValue(Number(e.target.value))}
                className="w-full h-2 bg-indigo-100 rounded-lg appearance-none cursor-pointer accent-indigo-600"
              />
            </div>

            <div>
              <div className="flex justify-between mb-4">
                <span className="text-sm font-bold text-zinc-700">Posting Frequency (Weekly)</span>
                <span className="text-sm font-black text-indigo-600">{postsPerWeek} posts</span>
              </div>
              <input 
                type="range" min="1" max="7" step="1" 
                value={postsPerWeek} onChange={(e) => setPostsPerWeek(Number(e.target.value))}
                className="w-full h-2 bg-indigo-100 rounded-lg appearance-none cursor-pointer accent-indigo-600"
              />
            </div>

            <div>
              <div className="flex justify-between mb-4">
                <span className="text-sm font-bold text-zinc-700">Your Hourly Value</span>
                <span className="text-sm font-black text-indigo-600">{symbol}{hourlyRate}/hr</span>
              </div>
              <input 
                type="range" min="50" max="1000" step="50" 
                value={hourlyRate} onChange={(e) => setHourlyRate(Number(e.target.value))}
                className="w-full h-2 bg-indigo-100 rounded-lg appearance-none cursor-pointer accent-indigo-600"
              />
            </div>
          </div>
        </div>

        <div className="lg:w-1/2 flex flex-col gap-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 h-full">
            <div className="bg-zinc-50 border border-zinc-200 p-6 rounded-3xl flex flex-col justify-between">
              <div className="w-10 h-10 bg-white rounded-xl shadow-sm border border-zinc-200 flex items-center justify-center mb-4">
                <Clock className="w-5 h-5 text-indigo-600" />
              </div>
              <div>
                <div className="text-3xl font-black text-zinc-900 mb-1">{hoursSavedYearly} Hr</div>
                <div className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest">Time Saved / Year</div>
              </div>
            </div>

            <div className="bg-zinc-50 border border-zinc-100 p-6 rounded-3xl flex flex-col justify-between">
              <div className="w-10 h-10 bg-white rounded-xl shadow-sm border border-zinc-200 flex items-center justify-center mb-4">
                <Zap className="w-5 h-5 text-amber-500" />
              </div>
              <div>
                <div className="text-3xl font-black text-zinc-900 mb-1">{symbol}{timeValueSaved.toLocaleString()}</div>
                <div className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest">Efficiency Value</div>
              </div>
            </div>

            <div className="md:col-span-2 bg-gradient-to-br from-indigo-600 to-[#8C7BFF] p-8 rounded-3xl shadow-xl shadow-indigo-200 text-white relative overflow-hidden">
              <div className="absolute top-0 right-0 w-32 h-32 bg-white/10 blur-2xl rounded-full" />
              <div className="flex justify-between items-end relative z-10">
                <div>
                  <div className="text-[10px] font-bold uppercase tracking-[0.2em] mb-2 opacity-80">Estimated Authority ROI</div>
                  <div className="text-5xl font-black mb-1">{symbol}{totalROI.toLocaleString()}</div>
                  <div className="text-xs font-bold opacity-80 flex items-center gap-1">
                    <TrendingUp className="w-3.5 h-3.5" /> Conservative annual outlook
                  </div>
                </div>
                <div className="hidden sm:block text-right">
                  <div className="text-[10px] font-bold uppercase tracking-widest bg-white/20 px-3 py-1 rounded-full mb-3">Est. Payback Period</div>
                  <div className="text-xl font-bold">14 Days</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
