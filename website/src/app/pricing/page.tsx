"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { InteractiveGrid } from "@/components/ui/InteractiveGrid";
import { MagneticButton } from "@/components/ui/MagneticButton";
import Link from "next/link";
import Script from "next/script";
import { Check, Info, ArrowRight, ShieldCheck, HelpCircle, Sparkles, BarChart3, Globe } from "lucide-react";
import { clsx } from "clsx";
import { RevenueCalculator } from "@/components/ui/RevenueCalculator";

type Region = "IN" | "ROW";

interface Plan {
  id: string;
  name: string;
  tagline: string;
  description: string;
  priceMonthly: string;
  priceYearly: string;
  interval: string;
  features: string[];
  notIncluded?: string[];
  limits?: string[];
  premiumFeature?: string;
  bonus?: string[];
  cta: string;
  badge?: string;
  recommended?: boolean;
  footerLine?: string;
}

const PRICING_DATA: Record<Region, { 
  currency: string; 
  symbol: string; 
  plans: Plan[]; 
  latte: string; 
  lunch: string; 
  annualCost: number; 
  defaultPipeline: number; 
  maxPipeline: number;
  locale: string;
}> = {
  IN: {
    currency: "INR",
    symbol: "₹",
    locale: "en-IN",
    annualCost: 19190,
    defaultPipeline: 5000000,
    maxPipeline: 50000000,
    latte: "599",
    lunch: "1,999",
    plans: [
      {
        id: "free",
        name: "Free",
        tagline: "Get started with AI-powered LinkedIn posts",
        description: "Try the platform and experience AI-generated LinkedIn content in seconds.",
        priceMonthly: "0",
        priceYearly: "0",
        interval: "/ month",
        features: [
          "3 AI-generated posts / month",
          "Basic post generation",
          "Limited repurpose support",
          "Preview & manual copy",
          "Velank branding on posts"
        ],
        notIncluded: [
          "Scheduling",
          "Knowledge base",
          "Style clone",
          "Analytics"
        ],
        cta: "👉 Get Started Free",
        footerLine: "No credit card required"
      },
      {
        id: "starter",
        name: "Starter",
        tagline: "Stay consistent on LinkedIn",
        description: "Perfect for job seekers and beginners building their personal brand.",
        priceMonthly: "599",
        priceYearly: "5,750",
        interval: "/ month",
        features: [
          "30 AI-generated posts / month",
          "Schedule up to 7 posts",
          "Repurpose content (text & links)",
          "Basic style cloning (1 writing style)",
          "Basic post variations"
        ],
        limits: ["Knowledge base: up to 5MB"],
        notIncluded: [
          "Advanced analytics",
          "Story series",
          "Best time to post"
        ],
        cta: "👉 Start Posting Consistently",
        badge: "Popular for Beginners"
      },
      {
        id: "creator",
        name: "Creator",
        tagline: "Build authority & grow faster",
        description: "For creators, founders, and professionals serious about LinkedIn growth.",
        priceMonthly: "1,999",
        priceYearly: "19,190",
        interval: "/ month",
        features: [
          "150 AI-generated posts / month",
          "Unlimited scheduling",
          "Advanced repurpose engine",
          "Style cloning (multiple styles)",
          "Knowledge base (up to 50MB)",
          "Best time to post (AI insights)",
          "Analytics & performance tracking"
        ],
        premiumFeature: "Story Series Engine (create 10–15 post campaigns)",
        cta: "👉 Grow My LinkedIn",
        badge: "Best Value",
        recommended: true
      },
      {
        id: "pro",
        name: "Pro",
        tagline: "Turn LinkedIn into a growth engine",
        description: "For founders, agencies, and power users scaling content and leads.",
        priceMonthly: "4,999",
        priceYearly: "47,990",
        interval: "/ month",
        features: [
          "500 AI-generated posts / month",
          "Priority generation (faster + better output)",
          "Advanced story campaigns",
          "Multiple knowledge bases",
          "Knowledge base limit up to 200MB",
          "Team access (up to 5 users)",
          "Advanced analytics dashboard",
          "Priority support"
        ],
        bonus: [
          "Early access to new features",
          "API access (coming soon)"
        ],
        cta: "👉 Scale My Content",
        badge: "Recommended for Teams"
      }
    ]
  },
  ROW: {
    currency: "USD",
    symbol: "$",
    locale: "en-US",
    annualCost: 278,
    defaultPipeline: 250000,
    maxPipeline: 2500000,
    latte: "19", 
    lunch: "29",
    plans: [
      {
        id: "free",
        name: "Free",
        tagline: "Get started with AI-powered LinkedIn posts",
        description: "Try the platform and experience AI-generated LinkedIn content in seconds.",
        priceMonthly: "0",
        priceYearly: "0",
        interval: "/ month",
        features: [
          "3 AI-generated posts / month",
          "Basic post generation",
          "Limited repurpose support",
          "Preview & manual copy",
          "Velank branding on posts"
        ],
        notIncluded: [
          "Scheduling",
          "Knowledge base",
          "Style clone",
          "Analytics"
        ],
        cta: "👉 Get Started Free",
        footerLine: "No credit card required"
      },
      {
        id: "starter",
        name: "Starter",
        tagline: "Stay consistent on LinkedIn",
        description: "Perfect for job seekers and beginners building their personal brand.",
        priceMonthly: "19",
        priceYearly: "182",
        interval: "/ month",
        features: [
          "30 AI-generated posts / month",
          "Schedule up to 7 posts",
          "Repurpose content (text & links)",
          "Basic style cloning (1 writing style)",
          "Basic post variations"
        ],
        limits: ["Knowledge base: up to 5MB"],
        notIncluded: [
          "Advanced analytics",
          "Story series",
          "Best time to post"
        ],
        cta: "👉 Start Posting Consistently",
        badge: "Popular for Beginners"
      },
      {
        id: "creator",
        name: "Creator",
        tagline: "Build authority & grow faster",
        description: "For creators, founders, and professionals serious about LinkedIn growth.",
        priceMonthly: "29",
        priceYearly: "278",
        interval: "/ month",
        features: [
          "150 AI-generated posts / month",
          "Unlimited scheduling",
          "Advanced repurpose engine",
          "Style cloning (multiple styles)",
          "Knowledge base (up to 50MB)",
          "Best time to post (AI insights)",
          "Analytics & performance tracking"
        ],
        premiumFeature: "Story Series Engine (create 10–15 post campaigns)",
        cta: "👉 Grow My LinkedIn",
        badge: "Best Value",
        recommended: true
      },
      {
        id: "pro",
        name: "Pro",
        tagline: "Turn LinkedIn into a growth engine",
        description: "For founders, agencies, and power users scaling content and leads.",
        priceMonthly: "55",
        priceYearly: "528",
        interval: "/ month",
        features: [
          "500 AI-generated posts / month",
          "Priority generation (faster + better output)",
          "Advanced story campaigns",
          "Multiple knowledge bases",
          "Knowledge base limit up to 200MB",
          "Team access (up to 5 users)",
          "Advanced analytics dashboard",
          "Priority support"
        ],
        bonus: [
          "Early access to new features",
          "API access (coming soon)"
        ],
        cta: "👉 Scale My Content",
        badge: "Recommended for Teams"
      }
    ]
  }
};

export default function Pricing() {
  const [region, setRegion] = useState<Region>("ROW");
  const [billingInterval, setBillingInterval] = useState<"monthly" | "yearly">("monthly");
  const [isDetecting, setIsDetecting] = useState(true);
  const [pipelineValue, setPipelineValue] = useState(region === 'IN' ? 5000000 : 250000); 
  const [conversionRate, setConversionRate] = useState(3); 

  useEffect(() => {
    const detectRegion = async () => {
      // Check for cached region first to prevent the "blink"
      const cachedRegion = localStorage.getItem('user_region') as Region;
      if (cachedRegion) {
        setRegion(cachedRegion);
        setPipelineValue(cachedRegion === 'IN' ? 1000000 : 100000);
        setIsDetecting(false);
      }

      try {
        const response = await fetch('https://ipapi.co/json/');
        const data = await response.json();
        const detectedRegion: Region = data.country_code === 'IN' ? 'IN' : 'ROW';
        
        // Update state and cache
        setRegion(detectedRegion);
        setPipelineValue(detectedRegion === 'IN' ? 1000000 : 100000);
        localStorage.setItem('user_region', detectedRegion);
      } catch (error) {
        console.error("Failed to detect region:", error);
        // Fallback to ROW if no cache and no detection
        if (!cachedRegion) {
          setRegion('ROW');
          setPipelineValue(100000);
        }
      } finally {
        setIsDetecting(false);
      }
    };
    detectRegion();
  }, []);


  // Handle cross-page hash scrolling
  useEffect(() => {
    if (!isDetecting && window.location.hash) {
      const id = window.location.hash.substring(1);
      setTimeout(() => {
        const el = document.getElementById(id);
        if (el) {
          const offset = 120; // Adjusted for header
          const bodyRect = document.body.getBoundingClientRect().top;
          const elementRect = el.getBoundingClientRect().top;
          const elementPosition = elementRect - bodyRect;
          const offsetPosition = elementPosition - offset;

          window.scrollTo({
            top: offsetPosition,
            behavior: "smooth"
          });
        }
      }, 300);
    }
  }, [isDetecting]);

  const currentData = PRICING_DATA[region];
  
  // Calculate ROI with Time Saving included
  const hoursSavedYearly = 150; // Average conservative estimate
  const hourlyRateVal = region === 'IN' ? 2500 : 75; // Hourly value of a founder's time
  const timeValueSaved = hoursSavedYearly * hourlyRateVal;
  
  const additionalRevenue = Math.round(pipelineValue * (conversionRate / 100));
  const estimatedMonthlyRevenue = Math.round(additionalRevenue / 12);
  const yearlyROI = Math.round(additionalRevenue + timeValueSaved - currentData.annualCost);
  const roiPercentage = currentData.annualCost > 0 ? Math.round((yearlyROI / currentData.annualCost) * 100) : 0;


  return (
    <div className="min-h-screen bg-zinc-50 text-zinc-900 relative flex flex-col pt-28 font-sans">
      <Header />
      <Script 
        src="https://checkout.razorpay.com/v1/checkout.js"
        strategy="lazyOnload"
      />
      {/* 1. Global Pricing Header & Plans */}
      <section className="pt-24 pb-32 md:pt-32 md:pb-48 relative overflow-hidden bg-white">
        <InteractiveGrid />
        
        {/* Modern Background Accents */}
        <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-indigo-50/40 rounded-full blur-[100px] pointer-events-none -translate-y-1/2 translate-x-1/4" />
        <div className="absolute bottom-0 left-0 w-[400px] h-[400px] bg-blue-50/30 rounded-full blur-[80px] pointer-events-none translate-y-1/2 -translate-x-1/4" />
        
        <div className="w-full max-w-7xl mx-auto px-4 sm:px-6 md:px-8 relative z-10 text-center">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
          >
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-50/80 border border-indigo-100/50 text-[10px] font-bold tracking-[0.2em] uppercase text-indigo-600 mb-6 backdrop-blur-sm">
              Premium Outcome-Based Pricing
            </div>
            
            <h1 className="text-4xl md:text-6xl lg:text-7xl font-black tracking-tight mb-6 text-zinc-900 leading-[1.1]">
              Invest in your <br/>
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-600 via-violet-600 to-blue-500">Digital Equity.</span>
            </h1>
            
            <p className="text-lg md:text-xl text-zinc-500 mb-12 max-w-2xl mx-auto font-medium leading-relaxed">
              Velank AI is your automated outbound engine. <br className="hidden md:block"/>
              <span className="text-zinc-900 font-semibold italic">Build trust while you sleep.</span>
            </p>

            {/* Billing Toggle - Ultra Sleek */}
            <div className="flex flex-col items-center gap-6 mb-16 md:mb-24">
              <div className="flex items-center gap-1 bg-zinc-100 p-1 rounded-2xl border border-zinc-200 shadow-inner">
                <button
                  onClick={() => setBillingInterval("monthly")}
                  className={clsx(
                    "px-6 py-2 rounded-xl font-bold transition-all text-xs md:text-sm",
                    billingInterval === "monthly" 
                      ? "bg-white text-zinc-900 shadow-sm" 
                      : "text-zinc-400 hover:text-zinc-600"
                  )}
                >
                  Monthly
                </button>
                <button
                  onClick={() => setBillingInterval("yearly")}
                  className={clsx(
                    "px-6 py-2 rounded-xl font-bold transition-all text-xs md:text-sm flex items-center gap-2",
                    billingInterval === "yearly" 
                      ? "bg-white text-zinc-900 shadow-sm" 
                      : "text-zinc-400 hover:text-zinc-600"
                  )}
                >
                  Yearly
                  <span className="bg-indigo-600 text-white text-[9px] px-2 py-0.5 rounded-full font-black uppercase">
                    -20%
                  </span>
                </button>
              </div>
              
              <AnimatePresence mode="wait">
                {billingInterval === "yearly" && (
                  <motion.div 
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.95 }}
                    className="text-indigo-600 font-bold text-xs bg-indigo-50/80 px-4 py-1.5 rounded-full border border-indigo-100/50 flex items-center gap-2"
                  >
                    <Sparkles className="w-3.5 h-3.5" />
                    Save {region === 'IN' ? `₹${(1999 * 12 - 19190).toLocaleString()}` : `$${(24 * 12 - 230).toLocaleString()}`} yearly on Creator
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </motion.div>
          
          {/* Pricing Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 xl:grid-cols-4 gap-6 xl:gap-8 items-stretch w-full">
            {currentData.plans.map((plan, idx) => {
              const displayPrice = billingInterval === "monthly" ? plan.priceMonthly : plan.priceYearly;
              const displayInterval = billingInterval === "monthly" ? "/ mo" : "/ yr";
              const isCreator = plan.id === 'creator';
              const isPro = plan.id === 'pro';
              
              return (
                <motion.div 
                  key={plan.id}
                  id={plan.id}
                  initial={{ opacity: 0, y: 40 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.8, delay: idx * 0.1, ease: [0.16, 1, 0.3, 1] }}
                  viewport={{ once: true }}
                  className={clsx(
                    "flex flex-col h-full relative group rounded-[2.5rem] transition-all duration-700",
                    isCreator 
                      ? "z-10 xl:scale-[1.05] ring-1 ring-indigo-500/20 shadow-[0_40px_100px_rgba(106,85,225,0.1)]" 
                      : "z-0 hover:-translate-y-2"
                  )}
                >
                  {/* Glass Card Layer with Sophisticated Depth */}
                  <div className={clsx(
                    "absolute inset-0 rounded-[2.5rem] transition-all duration-700",
                    isCreator 
                      ? "bg-white border-2 border-[#6A55E1] shadow-[0_40px_100px_rgba(106,85,225,0.2)]" 
                      : "bg-white/90 backdrop-blur-xl border border-zinc-200/60 shadow-[0_8px_30px_rgb(0,0,0,0.04)] group-hover:shadow-[0_40px_80px_rgba(0,0,0,0.06)]"
                  )} />

                  {/* Mesh Gradient Background for Premium Tiers */}
                  {(isCreator || isPro) && (
                    <div className={clsx(
                      "absolute inset-0 rounded-[2.5rem] overflow-hidden -z-10 transition-opacity duration-700",
                      isCreator ? "opacity-[0.03] group-hover:opacity-[0.05]" : "opacity-0 group-hover:opacity-[0.02]"
                    )}>
                      <div className="absolute inset-0 bg-brand-mesh scale-150 blur-3xl animate-pulse" />
                    </div>
                  )}

                  {plan.badge && (
                    <div className={clsx(
                      "absolute top-0 left-10 -translate-y-1/2 px-4 py-2 text-white text-[9px] font-black rounded-full tracking-[0.2em] uppercase shadow-xl flex items-center gap-2 border whitespace-nowrap z-20",
                      isCreator ? "bg-[#6A55E1] border-white/20" : "bg-zinc-900 border-zinc-700"
                    )}>
                      {isCreator && <Sparkles className="w-3 h-3 fill-white" />}
                      {plan.badge}
                    </div>
                  )}
                  
                  {/* Card Content - Now Left-Aligned for Premium Reading Flow */}
                  <div className="relative z-10 p-8 xl:p-10 flex flex-col h-full text-left">
                    <div className="mb-10">
                      <h3 className={clsx(
                        "text-[10px] font-black uppercase tracking-[0.4em] mb-6 transition-colors",
                        isCreator ? "text-[#6A55E1]" : "text-zinc-400 group-hover:text-zinc-600"
                      )}>
                        {plan.name}
                      </h3>
                      
                      <div className="flex items-baseline gap-1 mb-2">
                        <span className="text-zinc-400 font-bold text-lg self-start mt-1.5">{currentData.symbol}</span>
                        <span className={clsx(
                          "font-black text-zinc-900 tracking-tighter leading-none transition-all",
                          isCreator ? "text-5xl xl:text-6xl" : "text-4xl xl:text-5xl"
                        )}>
                          {displayPrice}
                        </span>
                        {plan.id !== 'free' && (
                          <span className="text-zinc-400 font-black text-[10px] uppercase tracking-widest ml-2">{displayInterval}</span>
                        )}
                      </div>
                      
                      <p className={clsx(
                        "text-[10px] font-black uppercase tracking-[0.15em] mb-6",
                        isCreator ? "text-indigo-600/60" : "text-zinc-400"
                      )}>
                        {plan.tagline}
                      </p>
                      
                      <p className={clsx(
                        "text-xs font-semibold leading-relaxed max-w-[90%]",
                        isCreator ? "text-indigo-900/70" : "text-zinc-500"
                      )}>
                        {plan.description}
                      </p>
                    </div>
                    
                    <div className="space-y-8 mb-12 flex-1">
                      <div className="space-y-5">
                        <p className="text-[9px] font-black text-zinc-400 uppercase tracking-[0.2em]">What&apos;s included</p>
                        <ul className="space-y-4">
                          {plan.features.map((feature, i) => (
                            <li key={i} className="flex gap-4 text-xs xl:text-[13px] text-zinc-600 font-bold items-start group/item">
                              <div className={clsx(
                                "w-5 h-5 rounded-lg flex items-center justify-center shrink-0 mt-0.5 transition-all shadow-sm",
                                isCreator 
                                  ? "bg-indigo-600 border border-indigo-400 text-white" 
                                  : "bg-white border border-zinc-200 text-zinc-500 group-hover/item:border-indigo-200 group-hover/item:text-indigo-600"
                              )}>
                                <Check className="w-3 h-3 stroke-[3]" />
                              </div>
                              <span className={clsx(
                                "transition-colors leading-snug pt-0.5", 
                                isCreator ? "text-zinc-900" : "text-zinc-600 group-hover:text-zinc-900"
                              )}>
                                {feature}
                              </span>
                            </li>
                          ))}
                        </ul>
                      </div>

                      {plan.premiumFeature && (
                        <div className="bg-indigo-50/40 p-5 rounded-[2rem] border border-indigo-100/50 group/premium hover:bg-indigo-50 transition-all cursor-default">
                          <div className="flex items-center gap-2 mb-3">
                            <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
                            <span className="text-[9px] font-black uppercase tracking-widest text-indigo-700">Premium Upgrade</span>
                          </div>
                          <p className="text-[11px] font-bold text-zinc-800 leading-normal">{plan.premiumFeature}</p>
                        </div>
                      )}

                      {(plan.limits || plan.notIncluded) && (
                        <div className="space-y-4 pt-8 border-t border-zinc-100/60">
                          {plan.limits?.map((limit, i) => (
                            <div key={i} className="flex items-center gap-4 text-[10px] font-black text-zinc-400 uppercase tracking-[0.1em]">
                              <div className="w-5 flex justify-center"><Info className="w-3.5 h-3.5 text-indigo-400" /></div>
                              {limit}
                            </div>
                          ))}
                          {plan.notIncluded?.map((item, i) => (
                            <div key={i} className="flex gap-4 items-center opacity-40 grayscale group/not">
                              <div className="w-5 flex justify-center text-[10px]">
                                <div className="w-1.5 h-1.5 rounded-full bg-zinc-400" />
                              </div>
                              <span className="text-[11px] font-bold text-zinc-500 line-through decoration-zinc-300 decoration-2">{item}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                    
                    <div className="mt-auto pt-6">
                      <Link 
                        href={`https://app.velank.io/login?plan=${plan.id}&interval=${billingInterval}`}
                        className={clsx(
                          "w-full flex flex-col items-center justify-center rounded-2xl font-black transition-all group/btn overflow-hidden relative h-16 xl:h-20 px-8",
                          isCreator 
                            ? "bg-[#6A55E1] text-white shadow-[0_20px_40px_rgba(106,85,225,0.3)] hover:bg-[#5a44d1] hover:scale-[1.02] active:scale-[0.98]" 
                            : "bg-zinc-900 text-white hover:bg-zinc-800 hover:scale-[1.02] active:scale-[0.98] shadow-xl"
                        )}
                      >
                        <div className="flex items-center justify-center gap-3 relative z-10 w-full">
                          <span className="uppercase tracking-[0.1em] text-[10px] md:text-xs text-center leading-tight">
                            {plan.cta}
                          </span>
                          <ArrowRight className={clsx(
                            "w-4 h-4 shrink-0 transition-transform duration-500 group-hover/btn:translate-x-2",
                            isCreator ? "text-white/80" : "text-white/60"
                          )} />
                        </div>
                        {plan.footerLine && (
                          <span className={clsx(
                            "text-[8px] font-black uppercase tracking-[0.2em] mt-2 relative z-10 opacity-60",
                            isCreator ? "text-indigo-200" : "text-zinc-400"
                          )}>
                            {plan.footerLine}
                          </span>
                        )}
                        {/* Interactive Shine Effect */}
                        <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent -translate-x-full group-hover:animate-[shine_1.5s_infinite] transition-transform" />
                      </Link>
                    </div>
                  </div>
                </motion.div>
              );
            })}
          </div>

          {/* Social Proof & Guarantees - Elite Style */}
          <div className="mt-24 md:mt-32 flex flex-col items-center gap-12">
            <motion.div 
              whileHover={{ scale: 1.02 }}
              className="flex items-center gap-3 px-8 py-4 bg-zinc-900 text-white rounded-[2rem] shadow-2xl group cursor-default transition-all"
            >
              <ShieldCheck className="w-5 h-5 text-emerald-400 group-hover:rotate-12 transition-transform" />
              <div className="flex flex-col items-start leading-none gap-1">
                <span className="text-[10px] font-black uppercase tracking-[0.2em] text-zinc-500">Zero Risk Guarantee</span>
                <span className="text-sm font-black uppercase tracking-widest">7-Day Free Trial On All Paid Plans</span>
              </div>
            </motion.div>

            <div className="space-y-8 w-full max-w-4xl opacity-50 grayscale hover:grayscale-0 hover:opacity-100 transition-all duration-700">
              <p className="text-[10px] font-black text-zinc-400 uppercase tracking-[0.4em] mb-8">Trusted by creators, job seekers & founders growing on LinkedIn</p>
              <div className="flex flex-wrap justify-center gap-8 md:gap-16">
                 {/* Placeholder for logos or trust marks */}
                 <div className="text-xl md:text-2xl font-black text-zinc-900 tracking-tighter italic">STRIPE</div>
                 <div className="text-xl md:text-2xl font-black text-zinc-900 tracking-tighter italic">RAZORPAY</div>
                 <div className="text-xl md:text-2xl font-black text-zinc-900 tracking-tighter italic">AWS</div>
                 <div className="text-xl md:text-2xl font-black text-zinc-900 tracking-tighter italic">REDIS</div>
                 <div className="text-xl md:text-2xl font-black text-zinc-900 tracking-tighter italic">POSTGRES</div>
              </div>
            </div>
          </div>
        </div>
      </section>


      {/* 4. Affordability Perspective - Redesigned Clinical Bento */}
      <section className="py-40 bg-white relative overflow-hidden">
        <div className="container mx-auto px-6 max-w-6xl relative z-10">
           <div className="text-center mb-24">
             <h2 className="text-xs font-bold tracking-[0.3em] text-indigo-600 uppercase mb-4">The Velank Way</h2>
             <h3 className="text-4xl md:text-7xl font-black text-zinc-900 tracking-tighter mb-8 leading-[1]">A fraction of <br/> incidental spend.</h3>
             <p className="text-xl text-zinc-500 max-w-2xl mx-auto font-medium leading-relaxed">
                authority investment vs. lifestyle consumption.
             </p>
           </div>

           <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
             <div className="bg-zinc-50/50 border border-zinc-100 rounded-[2rem] p-10 flex flex-col justify-between group hover:bg-white hover:shadow-xl transition-all duration-500">
                <div className="text-4xl mb-8 group-hover:scale-110 transition-transform origin-left">☕</div>
                <div>
                   <span className="text-xs font-bold text-zinc-400 uppercase tracking-widest block mb-1">One Café Latte/Day</span>
                   <span className="text-3xl font-black text-zinc-900 tracking-tighter">{currentData.symbol}{currentData.latte}<span className="text-sm text-zinc-400"> /mo</span></span>
                </div>
             </div>
             <div className="bg-zinc-50/50 border border-zinc-100 rounded-[2rem] p-10 flex flex-col justify-between group hover:bg-white hover:shadow-xl transition-all duration-500">
                <div className="text-4xl mb-8 group-hover:scale-110 transition-transform origin-left">🍱</div>
                <div>
                   <span className="text-xs font-bold text-zinc-400 uppercase tracking-widest block mb-1">App Delivery 3x/Week</span>
                   <span className="text-3xl font-black text-zinc-900 tracking-tighter">{currentData.symbol}{currentData.lunch}<span className="text-sm text-zinc-400"> /mo</span></span>
                </div>
             </div>
             <div className="bg-indigo-600 rounded-[2rem] p-10 flex flex-col justify-between shadow-2xl shadow-indigo-200 relative overflow-hidden group">
                <div className="absolute top-0 right-0 w-32 h-32 bg-white/10 rounded-full blur-2xl group-hover:scale-150 transition-transform duration-700" />
                <div className="text-4xl mb-8"><Sparkles className="w-10 h-10 text-white" /></div>
                <div className="relative z-10">
                   <span className="text-xs font-bold text-indigo-200 uppercase tracking-widest block mb-1">Velank AI (Annual)</span>
                   <span className="text-4xl font-black text-white tracking-tighter">{currentData.symbol}{Math.round(currentData.annualCost / 12).toLocaleString()}<span className="text-base text-indigo-200"> /mo</span></span>
                </div>
             </div>
           </div>

           <div className="bg-zinc-900 rounded-[2.5rem] p-12 md:p-16 flex flex-col md:flex-row gap-12 items-center text-left relative overflow-hidden group">
              <div className="absolute inset-0 bg-gradient-to-r from-indigo-500/10 to-transparent pointer-events-none" />
              <div className="w-24 h-24 bg-white/5 border border-white/10 rounded-3xl flex items-center justify-center shrink-0 shadow-2xl group-hover:rotate-6 transition-transform">
                <BarChart3 className="w-10 h-10 text-indigo-400" />
              </div>
              <div>
                <h4 className="text-3xl font-extrabold text-white mb-4 tracking-tight">Compounding Digital Assets.</h4>
                <p className="text-zinc-400 leading-relaxed font-semibold text-lg max-w-2xl">
                  Incidental lunches provide zero return. Velank AI is a productive asset. Every post you publish today creates a permanent &quot;Trust Node&quot; that generates inbound flow for years to come.
                </p>
              </div>
           </div>
        </div>
      </section>

      {/* 4.5 Revenue & ROI Calculator */}
      <section className="py-24 bg-white relative overflow-hidden overflow-x-hidden">
        <div className="container mx-auto px-6 max-w-6xl relative z-10">
          <RevenueCalculator symbol={currentData.symbol} />
        </div>
      </section>

      {/* 4.75 Lead Magnet - Strategy Guide */}
      <section className="py-24 bg-indigo-600 relative overflow-hidden isolate">
        <div className="absolute inset-0 bg-[url('https://res.cloudinary.com/dzbcnwqut/image/upload/v1703649553/grid_q29nt2.svg')] opacity-10 pointer-events-none" />
        <div className="absolute top-0 right-0 w-96 h-96 bg-white/10 blur-[100px] rounded-full -translate-y-1/2 translate-x-1/2" />
        
        <div className="container mx-auto px-6 max-w-5xl relative z-10 text-center">
          <div className="max-w-3xl mx-auto">
             <div className="inline-flex bg-white/20 px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-widest text-white mb-8">Free Resource</div>
             <h2 className="text-3xl md:text-5xl font-black text-white mb-8 tracking-tight leading-tight px-4">
               Not ready to automate? <br/> <span className="opacity-70 italic font-serif">Download the manual strategy.</span>
             </h2>
             <p className="text-xl text-indigo-100 mb-12 font-medium leading-relaxed px-4">
               Get our &apos;B2B Authority Blueprint&apos; - The 25-page guide we use to scale LinkedIn profiles from 0 to 100k+ impressions per month manually.
             </p>
             <form className="flex flex-col sm:flex-row gap-4 max-w-lg mx-auto p-2 bg-white/10 rounded-2xl border border-white/20 backdrop-blur-md">
               <input type="email" placeholder="Work email address..." className="flex-1 bg-transparent border-none outline-none text-white placeholder:text-indigo-200 px-4 py-3 font-medium h-12" required />
               <button type="submit" className="bg-white text-indigo-600 h-12 px-8 rounded-xl font-bold hover:bg-white/90 transition-all flex items-center justify-center gap-2 shadow-xl shrink-0 group">
                 Send it to me <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
               </button>
             </form>
             <p className="mt-6 text-[10px] font-bold text-indigo-200 uppercase tracking-widest">
               Joined by 20,000+ professionals • No spam • Unsubscribe anytime
             </p>
          </div>
        </div>
      </section>
      <section className="py-40 bg-zinc-50 relative overflow-hidden">
        <div className="container mx-auto px-6 max-w-6xl relative z-10">
           <h2 className="text-4xl md:text-6xl font-black text-center mb-24 text-zinc-900 tracking-tighter">Your concerns, <br/><span className="text-zinc-400">mitigated.</span></h2>
           <div className="grid md:grid-cols-2 gap-4 lg:gap-6">
             {[
               { q: "Is my data private?", a: "Your documents are encrypted and siloed. We never train our baseline models on your proprietary strategy. Your 'Digital Twin' belongs only to you. Velank takes privacy seriously." },
               { q: "Is my profile safe?", a: "Yes. Velank AI uses the official LinkedIn API via secure OAuth. We never ask for your password and publish purely within LinkedIn's compliance boundaries." },
               {
                 q: "No time to set this up.",
                 a: "You only need 10 minutes once. Upload 3 key PDFs, choose your tone. Velank AI runs on autopilot from there, saving you 10+ hours a week."
               },
               {
                 q: "I can just use free AI tools.",
                 a: "Free LLMs require heavy prompt engineering and daily manual input. Velank AI is a closed-loop system grounded only in your actual facts and strategy."
               },
               {
                 q: "What if audience hates AI posts?",
                 a: "They hate generic AI posts. Because Velank AI isolates your strategy docs, the output sounds exactly like you—just formatted for maximum LinkedIn read time."
               },
               {
                 q: "Too expensive right now.",
                 a: "If this lands you just one additional client or speaking gig this year, the platform pays for itself 100x over. It's an investment, not a cost."
               }
             ].map((item, i) => (
               <div key={i} className="p-8 lg:p-10 bg-white border border-zinc-200 rounded-[2.5rem] shadow-sm hover:shadow-xl hover:border-indigo-100 transition-all duration-500">
                  <h4 className="text-xl font-bold text-zinc-900 mb-4 flex items-center gap-4">
                    <div className="w-8 h-8 rounded-full bg-indigo-50 flex items-center justify-center shrink-0">
                      <HelpCircle className="w-4 h-4 text-indigo-600" />
                    </div>
                    {item.q}
                  </h4>
                  <p className="text-zinc-500 text-lg leading-relaxed font-medium pl-12 border-l border-zinc-100">
                    {item.a}
                  </p>
               </div>
             ))}
           </div>
        </div>
      </section>

      {/* 6. Guarantee / Risk Reversal - Premium High-Trust Certificate */}
      <section className="py-44 relative overflow-hidden bg-white border-t border-zinc-100">
        <div className="container mx-auto px-6 max-w-4xl relative z-10">
          <motion.div
            initial={{ opacity: 0, scale: 0.98 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            className="text-center p-12 md:p-20 bg-emerald-50/30 border border-emerald-100 rounded-[3rem] relative overflow-hidden shadow-2xl shadow-emerald-100/20"
          >
            <div className="absolute top-0 left-0 w-full h-2 bg-emerald-500" />
            <div className="w-24 h-24 bg-white rounded-[2rem] shadow-xl flex items-center justify-center mx-auto mb-10 border border-emerald-100">
              <ShieldCheck className="w-12 h-12 text-emerald-600" />
            </div>
            <h2 className="text-4xl md:text-6xl font-black mb-8 text-zinc-900 tracking-tighter">Limited Time <br/> <span className="text-emerald-600">30% Discount.</span></h2>
            <p className="text-xl text-zinc-600 mb-12 font-medium leading-relaxed max-w-2xl mx-auto">
               Yes. We are currently offering a limited 30% discount for new members. Secure your price now to lock in your Velank AI growth engine.
            </p>
            <Link href="https://app.velank.io/login" className="inline-flex items-center justify-center rounded-2xl font-black transition-all bg-zinc-900 text-white hover:bg-zinc-800 h-16 md:h-20 px-8 md:px-16 text-lg md:text-2xl shadow-2xl shadow-zinc-200 group transform active:scale-95">
               Unleash Your Authority <ArrowRight className="ml-3 w-5 h-5 md:w-6 md:h-6 group-hover:translate-x-1 transition-transform" />
            </Link>
          </motion.div>
        </div>
      </section>

      <Footer />
    </div>
  );
}
