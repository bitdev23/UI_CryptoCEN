"use client";

import { motion } from "framer-motion";
import { Quote, Star, ArrowRight } from "lucide-react";
import Image from "next/image";
import Link from "next/link";

const testimonials = [
  {
    name: "Marcus Thorne",
    role: "SaaS Founder @ CloudScale",
    image: "https://i.pravatar.cc/150?u=marcus",
    content: "Velank turned my rough strategy docs into a 3-month LinkedIn pipeline in one afternoon. It's the only AI that doesn't sound like a generic robot.",
    stats: "+148% Profile Views",
  },
  {
    name: "Sarah Jenkins",
    role: "B2B Marketing Consultant",
    image: "https://i.pravatar.cc/150?u=sarah",
    content: "I used to spend 10+ hours a week on LinkedIn content. Now it's under 30 minutes. My 'Digital Twin' perfectly captures my tone and methodology.",
    stats: "32 Inbound Leads",
  },
  {
    name: "David K.",
    role: "VP of Sales @ TechFlow",
    image: "https://i.pravatar.cc/150?u=david",
    content: "The contrarian post engine is a game changer. We're finally getting engagement from the VPs we've been trying to reach for years.",
    stats: "Top 1% Industry Rank",
  },
  {
    name: "Elena Rodriguez",
    role: "Fractional CMO",
    image: "https://i.pravatar.cc/150?u=elena",
    content: "Consistency was my biggest struggle. Velank handles everything from drafting to scheduling. It's like having a world-class ghostwriter on tap.",
    stats: "5.2M Impressions",
  },
  {
    name: "James Wilson",
    role: "CEO @ Nexus Agency",
    image: "https://i.pravatar.cc/150?u=james",
    content: "We migrated our entire executive ghostwriting workflow to Velank. The 'Knowledge Base' feature ensures we never ghostwrite something that doesn't fit the founder's brain.",
    stats: "Saved 20hrs/Week",
  },
  {
    name: "Jessica L.",
    role: "Content Strategy Lead",
    image: "https://i.pravatar.cc/150?u=jessica",
    content: "The ROI was immediate. Within 2 weeks of using Velank, our inbound pipeline grew by 40%. The posts are actually original because they come from our data.",
    stats: "$120k Pipeline",
  }
];

export function WallOfLove() {
  return (
    <section className="py-32 bg-zinc-900 overflow-hidden relative border-t border-zinc-800">
      {/* Dynamic Background */}
      <div className="absolute top-0 right-0 w-[800px] h-[800px] bg-indigo-500/10 rounded-full blur-[120px] pointer-events-none -translate-y-1/2 translate-x-1/2" />
      <div className="absolute bottom-0 left-0 w-[600px] h-[600px] bg-blue-500/5 rounded-full blur-[100px] pointer-events-none translate-y-1/2 -translate-x-1/2" />
      
      <div className="container mx-auto px-6 max-w-7xl relative z-10">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-12 mb-20 text-center md:text-left">
          <div className="max-w-2xl">
            <h2 className="text-indigo-400 font-bold tracking-[0.3em] uppercase text-xs mb-6">Social Proof</h2>
            <h3 className="text-4xl md:text-7xl font-black text-white tracking-tighter leading-[1] mb-6">
              The Wall <br className="hidden md:block" /> of <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-indigo-100 italic">Love.</span>
            </h3>
            <p className="text-xl text-zinc-400 font-medium leading-relaxed">
              Join 20,000+ founders and leaders who have stopped the &quot;LinkedIn Grind&quot; and started building actual authority.
            </p>
          </div>
          <div className="flex gap-4 items-center justify-center md:justify-start">
            <div className="flex flex-col">
              <div className="text-4xl font-black text-white mb-1">4.9/5</div>
              <div className="flex text-amber-500 gap-0.5">
                {[...Array(5)].map((_, i) => <Star key={i} className="w-4 h-4 fill-amber-500" />)}
              </div>
              <div className="text-[10px] text-zinc-500 font-bold uppercase tracking-widest mt-2">Average User Rating</div>
            </div>
            <div className="w-px h-16 bg-zinc-800 hidden md:block mx-4" />
            <div className="flex flex-col">
              <div className="text-4xl font-black text-white mb-1">20k+</div>
              <div className="text-[10px] text-zinc-500 font-bold uppercase tracking-widest mt-2">Daily Active Posts</div>
            </div>
          </div>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {testimonials.map((t, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1 }}
              viewport={{ once: true }}
              className="bg-zinc-800/40 backdrop-blur-sm border border-white/5 rounded-[2.5rem] p-8 md:p-10 flex flex-col hover:bg-zinc-800/60 hover:border-indigo-500/20 hover:shadow-2xl hover:shadow-indigo-500/5 transition-all group"
            >
              <div className="flex items-center gap-4 mb-8">
                <div className="w-14 h-14 relative rounded-2xl overflow-hidden border border-white/10 shadow-xl group-hover:scale-110 transition-transform duration-500">
                  <Image src={t.image} alt={t.name} fill className="object-cover" />
                </div>
                <div>
                  <div className="font-bold text-white text-lg tracking-tight group-hover:text-indigo-200 transition-colors">{t.name}</div>
                  <div className="text-xs text-zinc-500 font-bold uppercase tracking-widest leading-tight">{t.role}</div>
                </div>
              </div>
              
              <div className="relative mb-8">
                <Quote className="w-12 h-12 text-indigo-500/20 absolute -top-4 -left-4 -rotate-12 group-hover:rotate-0 transition-transform duration-700" />
                <p className="text-zinc-300 text-lg leading-relaxed font-medium relative z-10">&quot;{t.content}&quot;</p>
              </div>

              <div className="mt-auto pt-8 border-t border-white/5 flex items-center justify-between">
                <div className="flex flex-col">
                  <div className="text-xs font-bold text-zinc-500 uppercase tracking-[0.2em] mb-1">Verified Result</div>
                  <div className="text-indigo-400 font-black text-lg tracking-tighter">{t.stats}</div>
                </div>
                <div className="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                   <ArrowRight className="w-5 h-5 text-indigo-400" />
                </div>
              </div>
            </motion.div>
          ))}
        </div>

        <div className="mt-20 text-center">
          <Link 
            href="/pricing"
            className="inline-flex items-center gap-2.5 px-8 py-4 rounded-2xl bg-indigo-600 text-white font-black hover:bg-indigo-700 transition-all shadow-xl shadow-indigo-600/20 active:scale-95 group"
          >
            Start Your Own Success Story <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
          </Link>
        </div>
      </div>
    </section>
  );
}
