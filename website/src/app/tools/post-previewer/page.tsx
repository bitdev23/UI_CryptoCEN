"use client";

import { useState } from "react";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { Smartphone, Monitor, Type, Info } from "lucide-react";
import { PoweredByVelank } from "@/components/ui/PoweredByVelank";

export default function PostPreviewer() {
  const [content, setContent] = useState("");
  const [view, setView] = useState<"desktop" | "mobile">("mobile");

  const charCount = content.length;

  return (
    <div className="min-h-screen bg-white text-zinc-900 relative flex flex-col pt-28 font-sans">
      <Header />
      
      <main className="flex-1 container mx-auto px-6 py-20 max-w-6xl">
        <div className="text-center mb-16">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-50 border border-indigo-100 text-[10px] font-bold tracking-widest uppercase text-indigo-600 mb-6">
             Formatting Tool
          </div>
          <h1 className="text-4xl md:text-6xl font-black mb-6 tracking-tighter text-zinc-900">
            LinkedIn <span className="text-indigo-600">Post</span> Previewer.
          </h1>
          <p className="text-xl text-zinc-500 font-medium max-w-2xl mx-auto leading-relaxed">
            Don&apos;t let your hook get cut off. Preview exactly how your post looks on mobile and desktop before you hit publish.
          </p>
        </div>

        <div className="grid lg:grid-cols-2 gap-12">
          {/* Input Side */}
          <div className="space-y-6">
            <div className="bg-zinc-50 border border-zinc-200 rounded-[2.5rem] p-8 shadow-sm">
              <div className="flex justify-between items-center mb-4">
                <label className="text-xs font-bold text-zinc-400 uppercase tracking-widest flex items-center gap-2">
                  <Type className="w-4 h-4" /> Your Post Content
                </label>
                <div className="flex gap-4 text-[10px] font-black uppercase tracking-widest">
                   <span className={charCount > 3000 ? "text-red-500" : "text-zinc-400"}>{charCount} / 3000 Chars</span>
                </div>
              </div>
              <textarea 
                value={content}
                onChange={(e) => setContent(e.target.value)}
                placeholder="Paste your LinkedIn post here..."
                className="w-full h-80 bg-white border border-zinc-200 rounded-3xl p-6 text-base focus:outline-none focus:ring-2 focus:ring-indigo-500/20 transition-all resize-none shadow-inner"
              />
              <div className="mt-6 p-4 bg-indigo-50/50 border border-indigo-100 rounded-2xl flex items-start gap-3">
                 <Info className="w-5 h-5 text-indigo-600 shrink-0 mt-0.5" />
                 <p className="text-xs text-indigo-800 leading-relaxed font-medium">
                   <strong>Pro Tip:</strong> LinkedIn mobile usually cuts off text after ~140 characters or 3-5 lines. Keep your first two lines extremely punchy to stop the scroll.
                 </p>
              </div>
            </div>
          </div>

          {/* Preview Side */}
          <div className="space-y-6">
             <div className="flex items-center gap-2 mb-2 p-1 bg-zinc-100 rounded-2xl w-fit">
                <button 
                  onClick={() => setView("mobile")}
                  className={`flex items-center gap-2 px-6 py-2.5 rounded-xl text-xs font-bold transition-all ${view === "mobile" ? "bg-white text-zinc-900 shadow-sm" : "text-zinc-400 hover:text-zinc-600"}`}
                >
                  <Smartphone className="w-4 h-4" /> Mobile
                </button>
                <button 
                  onClick={() => setView("desktop")}
                  className={`flex items-center gap-2 px-6 py-2.5 rounded-xl text-xs font-bold transition-all ${view === "desktop" ? "bg-white text-zinc-900 shadow-sm" : "text-zinc-400 hover:text-zinc-600"}`}
                >
                  <Monitor className="w-4 h-4" /> Desktop
                </button>
             </div>

             <div className="relative flex justify-center">
                {view === "mobile" ? (
                  // Mobile Mockup
                  <div className="w-[320px] bg-white border-[8px] border-zinc-900 rounded-[3rem] shadow-2xl overflow-hidden relative">
                     <div className="h-6 w-full flex justify-center items-center">
                        <div className="w-20 h-4 bg-zinc-900 rounded-b-xl" />
                     </div>
                     <div className="p-4 border-b border-zinc-100 flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-zinc-200" />
                        <div className="space-y-1">
                           <div className="w-24 h-2.5 bg-zinc-200 rounded-full" />
                           <div className="w-16 h-2 bg-zinc-100 rounded-full" />
                        </div>
                     </div>
                     <div className="p-4">
                        <p className="text-[13px] leading-snug whitespace-pre-wrap text-zinc-800">
                          {content || "Your content will appear here..."}
                        </p>
                        {content.length > 140 && (
                          <span className="text-zinc-400 text-[13px] font-bold">...see more</span>
                        )}
                     </div>
                     <div className="h-12 border-t border-zinc-100 flex items-center justify-around px-4">
                        <div className="w-4 h-4 rounded bg-zinc-100" />
                        <div className="w-4 h-4 rounded bg-zinc-100" />
                        <div className="w-4 h-4 rounded bg-zinc-100" />
                     </div>
                  </div>
                ) : (
                  // Desktop Mockup
                  <div className="w-full max-w-[550px] bg-white border border-zinc-200 rounded-xl shadow-xl overflow-hidden">
                     <div className="p-4 border-b border-zinc-100 flex items-center gap-3">
                        <div className="w-12 h-12 rounded-full bg-zinc-200" />
                        <div className="space-y-1.5">
                           <div className="w-32 h-3 bg-zinc-200 rounded-full" />
                           <div className="w-24 h-2 bg-zinc-100 rounded-full" />
                        </div>
                     </div>
                     <div className="p-4">
                        <p className="text-sm leading-relaxed whitespace-pre-wrap text-zinc-800">
                          {content || "Your content will appear here..."}
                        </p>
                        {content.split('\n').length > 4 && (
                          <span className="text-zinc-400 text-sm font-bold mt-1 inline-block">...see more</span>
                        )}
                     </div>
                     <div className="p-4 border-t border-zinc-50 flex items-center justify-between">
                        <div className="flex gap-4">
                           <div className="w-8 h-8 rounded-full bg-zinc-50" />
                           <div className="w-8 h-8 rounded-full bg-zinc-50" />
                        </div>
                     </div>
                  </div>
                )}
             </div>
            
            <PoweredByVelank />
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}
