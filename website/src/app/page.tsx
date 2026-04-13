"use client";

import { motion, useInView, useMotionValue, useTransform, animate } from "framer-motion";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { InteractiveGrid } from "@/components/ui/InteractiveGrid";
import { MagneticButton } from "@/components/ui/MagneticButton";
import Link from "next/link";
import { CheckCircle2, PlayCircle, Sparkles, HelpCircle, TrendingUp, Users, ArrowRight, FileText, BarChart3, Clock, LayoutDashboard, Code2, Target, Calculator } from "lucide-react";
import { useState, useEffect, useRef } from "react";
import Image from "next/image";
import { WallOfLove } from "@/components/ui/WallOfLove";

function StatCounter({ value, isDecimal, prefix = "", suffix = "" }: { value: number, isDecimal?: boolean, prefix?: string, suffix?: string }) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true, margin: "-50px" });
  const motionValue = useMotionValue(0);
  const displayValue = useTransform(motionValue, (latest) => {
    let numStr = isDecimal ? latest.toFixed(1) : Math.round(latest).toString();
    if (!isDecimal && value >= 1000) {
      numStr = Math.round(latest).toLocaleString("en-US");
    }
    return prefix + numStr + suffix;
  });

  useEffect(() => {
    if (inView) {
      const controls = animate(motionValue, value, { duration: 2.5, ease: [0.16, 1, 0.3, 1] });
      return controls.stop;
    }
  }, [inView, value, motionValue]);

  return <motion.span ref={ref}>{displayValue}</motion.span>;
}

export default function Home() {
  const [sliderPos, setSliderPos] = useState(50);
  const [showStickyCTA, setShowStickyCTA] = useState(false);
  const [activeStep, setActiveStep] = useState(0);
  const [isPreviewLoading, setIsPreviewLoading] = useState(false);
  const [hasPreviewed, setHasPreviewed] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [particles, setParticles] = useState<Array<{
    startX: number;
    startY: number;
    moveX: number;
    duration: number;
    delay: number;
  }>>([]);

  useEffect(() => {
    const timer = setTimeout(() => {
      setMounted(true);
      setParticles([...Array(8)].map(() => ({
        startX: Math.random() * 600,
        startY: Math.random() * 400,
        moveX: (Math.random() - 0.5) * 30,
        duration: 4 + Math.random() * 4,
        delay: Math.random() * 5
      })));
    }, 0);
    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    // Handle cross-page hash scrolling
    if (window.location.hash) {
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
      }, 600);
    }

    const handleScroll = () => {
      setShowStickyCTA(window.scrollY > 1200);

      const stepElements = document.querySelectorAll('.workflow-step');
      let currentStep = 0;

      // Calculate which step is most prominent in the viewport
      const viewportHeight = window.innerHeight;
      const centerPoint = viewportHeight * 0.5;

      let minDistance = Infinity;

      stepElements.forEach((el, index) => {
        const rect = el.getBoundingClientRect();
        const stepCenter = rect.top + rect.height / 2;
        const distance = Math.abs(stepCenter - centerPoint);

        if (distance < minDistance) {
          minDistance = distance;
          currentStep = index;
        }
      });

      setActiveStep(currentStep);
    };

    handleScroll();
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  return (
    <div className="min-h-screen bg-zinc-50 text-zinc-900 relative flex flex-col pt-28 md:pt-32 font-sans">
      <Header />

      {/* 1. Hero Section */}
      <section className="relative pt-16 md:pt-24 pb-32 overflow-hidden border-b border-zinc-200">
        {/* Interactive Canvas Grid */}
        <InteractiveGrid />
        <div className="absolute top-0 right-0 w-[600px] h-[600px] bg-indigo-100 rounded-full blur-[120px] pointer-events-none -translate-y-1/2 translate-x-1/3" />
        <div className="absolute top-1/2 left-0 w-[400px] h-[400px] bg-blue-50 rounded-full blur-[100px] pointer-events-none -translate-y-1/2 -translate-x-1/3" />

        <div className="container mx-auto px-6 relative z-10 text-center max-w-6xl">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, ease: "easeOut" }}
          >
            <div className="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-full bg-indigo-50 border border-indigo-200 text-sm xl:text-xs font-semibold text-indigo-700 mb-8 shadow-sm tracking-wide shadow-indigo-500/10">
              <Sparkles className="w-4 h-4 text-indigo-500" />
              <span>Now live — 2.4 Enterprise</span>
              <ArrowRight className="w-3 h-3 ml-1" />
            </div>

            <h1 className="text-[2.75rem] md:text-7xl font-extrabold tracking-tight mb-8 leading-[1.1] text-zinc-900 drop-shadow-sm px-2">
              Stop losing deals to people who just <br className="hidden md:block" />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#6E56CF] via-[#818CF8] to-[#0D0B26]">
                show up more than you.
              </span>
            </h1>

            <p className="text-xl md:text-2xl text-zinc-600 mb-12 max-w-3xl mx-auto leading-relaxed font-medium">
              <span className="text-zinc-900 font-bold">LinkedIn is making someone rich right now. Just not you.</span><br className="hidden md:block"/>
              <span className="inline-block mt-2">Velank AI turns your existing expertise into consistent, strategic LinkedIn content — written from your knowledge, in your voice.</span>
            </p>

            <div className="flex flex-col items-center w-full max-w-4xl mx-auto space-y-6">
              {/* Secondary Link - TOP */}
              <Link 
                href="#demo" 
                className="inline-flex items-center gap-2.5 px-5 py-2.5 rounded-full bg-zinc-50 border border-zinc-200 text-zinc-600 hover:text-indigo-600 hover:border-indigo-100 hover:bg-indigo-50/50 transition-all active:scale-95 group shadow-sm mb-2"
              >
                <PlayCircle className="w-5 h-5 text-indigo-600 fill-indigo-600/10" />
                <span className="text-sm font-bold tracking-tight">Watch it work in 60 seconds</span>
                <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </Link>

              {/* Email/Industry Input Field - MIDDLE */}
              <form 
                onSubmit={(e) => { 
                  e.preventDefault(); 
                  const formData = new FormData(e.currentTarget);
                  const industry = formData.get('industry');
                  window.location.href = `https://app.velank.io/login?industry=${encodeURIComponent(industry as string)}`; 
                }} 
                className="w-full flex flex-col sm:flex-row items-center gap-3 p-2 bg-white rounded-[2rem] border border-zinc-200 shadow-2xl shadow-zinc-200/50 focus-within:ring-4 focus-within:ring-[#6E56CF]/20 focus-within:border-[#A19CFF] transition-all max-w-3xl"
              >
                <div className="flex-1 w-full pl-4 md:pl-6 flex items-center h-16">
                  <span className="text-2xl mr-4">🚀</span>
                  <input 
                    name="industry"
                    type="text" 
                    placeholder="Enter your industry and topic..." 
                    required 
                    className="w-full outline-none text-zinc-800 placeholder:text-zinc-400 bg-transparent text-lg md:text-xl font-medium" 
                  />
                </div>
                <MagneticButton className="w-full sm:w-auto">
                  <button type="submit" className="w-full inline-flex items-center justify-center rounded-2xl font-black transition-all bg-gradient-to-r from-[#6E56CF] to-[#818CF8] text-white hover:shadow-indigo-500/30 h-16 px-10 text-base md:text-lg shadow-xl shadow-[#6E56CF]/40 transform group">
                    <span>Generate your first post free</span>
                    <ArrowRight className="w-5 h-5 ml-2.5 group-hover:translate-x-1 transition-transform" />
                  </button>
                </MagneticButton>
              </form>
              
              {/* Trust Line - BOTTOM */}
              <p className="text-[10px] md:text-[11px] font-bold text-zinc-400 uppercase tracking-[0.2em] pt-2">
                No credit card · Works with your existing LinkedIn · Cancel anytime
              </p>
            </div>
            <div className="flex flex-col items-center justify-center mt-10 space-y-4">
              <div className="flex -space-x-3 opacity-90 hover:opacity-100 transition-opacity cursor-pointer">
                {[
                  "https://i.pravatar.cc/100?img=12",
                  "https://i.pravatar.cc/100?img=33",
                  "https://i.pravatar.cc/100?img=47",
                  "https://i.pravatar.cc/100?img=15",
                  "https://i.pravatar.cc/100?img=24",
                ].map((src, i) => (
                  <Image
                    key={i}
                    src={src}
                    alt="User"
                    width={40}
                    height={40}
                    className="w-10 h-10 rounded-full border-2 border-zinc-50 shadow-md object-cover transform hover:-translate-y-1 transition-transform relative z-10 hover:z-20"
                  />
                ))}
                <div className="w-10 h-10 rounded-full border-2 border-zinc-50 bg-[#6E56CF] text-white text-[10px] font-bold flex items-center justify-center shadow-md relative z-20">
                  20k+
                </div>
              </div>
              <div className="flex flex-col md:flex-row items-center justify-center gap-6 md:gap-12 w-full max-w-4xl mx-auto pt-6 border-t border-zinc-200">
                <div className="flex flex-col items-center justify-center gap-1.5 md:items-start md:w-1/2">
                  <div className="flex text-amber-500 gap-1 mb-1">
                    <span className="text-sm">★</span><span className="text-sm">★</span><span className="text-sm">★</span><span className="text-sm">★</span><span className="text-sm">★</span>
                  </div>
                  <p className="text-sm text-zinc-800 font-bold leading-relaxed text-center md:text-left">
                    &quot;25+ enterprise demos from inbound in 90 days.&quot;
                  </p>
                </div>

                <div className="hidden md:block w-px h-12 bg-zinc-200 mx-2" />

                <div className="flex flex-col items-center justify-center gap-1 md:items-start md:w-1/2">
                  <p className="text-xs text-zinc-500 font-bold uppercase tracking-widest flex items-center gap-1.5">
                    <Sparkles className="w-3 h-3 text-indigo-500" /> Trusted By
                  </p>
                  <p className="text-sm text-zinc-600 font-medium leading-relaxed text-center md:text-left">
                    <span className="font-bold text-zinc-900">200+</span> founders, <span className="font-bold text-zinc-900">30+</span> B2B agencies, and <span className="font-bold text-zinc-900">18,000+</span> professionals.
                  </p>
                </div>
              </div>
            </div>
          </motion.div>

          {/* Dashboard Placeholder - Light UI specific */}
          <motion.div
            initial={{ opacity: 0, y: 60, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            whileHover={{ y: -10, rotateX: 2, rotateY: -2, zIndex: 40 }}
            transition={{ duration: 0.8, delay: 0.3, ease: [0.21, 0.47, 0.32, 0.98] }}
            className="mt-20 relative mx-auto max-w-5xl group cursor-crosshair perspective-[2000px]"
            style={{ transformStyle: "preserve-3d" }}
          >
            <div className="absolute -inset-2 bg-gradient-to-r from-indigo-500 via-purple-500 to-blue-500 rounded-[2rem] blur-2xl opacity-20 group-hover:opacity-40 transition-opacity duration-700 pointer-events-none" />
            <div className="w-full lg:aspect-[16/10] min-h-[420px] md:min-h-[500px] bg-zinc-50 rounded-2xl border border-zinc-200 shadow-2xl overflow-hidden flex flex-col items-center justify-center text-center relative z-10 p-1 ring-1 ring-zinc-900/5">
              <div className="w-full h-12 bg-zinc-100 border-b border-zinc-200 flex items-center px-4 gap-2">
                <div className="flex gap-1.5">
                  <div className="w-3 h-3 rounded-full bg-red-400" />
                  <div className="w-3 h-3 rounded-full bg-amber-400" />
                  <div className="w-3 h-3 rounded-full bg-green-400" />
                </div>
                <div className="mx-auto w-1/3 h-6 bg-white rounded-md border border-zinc-200 shadow-sm flex justify-center items-center text-[10px] text-zinc-400 font-mono tracking-widest uppercase">app.velank.ai</div>
              </div>
              <div className="w-full flex-1 bg-[#F9FAFB] flex flex-col md:flex-row relative overflow-hidden text-left">
                {/* Sidebar - Restored Look + Animations */}
                <motion.div 
                  initial={{ x: -20, opacity: 0 }}
                  animate={{ x: 0, opacity: 1 }}
                  transition={{ duration: 0.6, delay: 0.1 }}
                  className="hidden md:flex w-56 bg-[#6E56CF] text-white flex-col pt-6 pb-4 shrink-0 shadow-[4px_0_24px_rgba(0,0,0,0.1)] relative z-20 overflow-hidden"
                >
                  {/* Subtle Liquid Background Glow */}
                  <motion.div 
                    animate={{ 
                      scale: [1, 1.1, 1],
                      opacity: [0.1, 0.15, 0.1],
                    }}
                    transition={{ duration: 10, repeat: Infinity, ease: "easeInOut" }}
                    className="absolute -top-10 -left-10 w-48 h-48 bg-white/20 rounded-full blur-[60px] pointer-events-none"
                  />

                  <div className="px-5 font-black flex items-center gap-2 mb-8 text-xl tracking-tight relative z-10">
                    <Sparkles className="w-6 h-6" /> Velank AI
                  </div>
                  
                  <div className="flex flex-col gap-1.5 px-3 relative z-10">
                    {[
                      { icon: LayoutDashboard, label: "Dashboard", active: false },
                      { icon: Sparkles, label: "LinkedIn Post", active: false },
                      { icon: Clock, label: "Scheduler", active: false },
                      { icon: FileText, label: "Database", active: true },
                      { icon: Users, label: "Settings", active: false },
                    ].map((item, i) => (
                      <motion.div
                        key={i}
                        initial={{ x: -10, opacity: 0 }}
                        animate={{ x: 0, opacity: 1 }}
                        transition={{ delay: 0.2 + i * 0.05 }}
                        className={`px-3 py-2 rounded-lg text-sm font-bold flex items-center gap-3 transition-colors relative group ${
                          item.active 
                            ? "bg-white/20 text-white shadow-inner border border-white/10" 
                            : "text-white/70 hover:bg-white/10"
                        }`}
                      >
                        {item.active && (
                          <motion.div 
                            layoutId="sidebarActive"
                            className="absolute left-0 w-1 h-4 bg-white rounded-r-full shadow-[0_0_8px_#fff]"
                          />
                        )}
                        <item.icon className={`w-4 h-4 ${item.active ? "opacity-100" : "opacity-70"}`} />
                        {item.label}
                      </motion.div>
                    ))}
                  </div>

                  <div className="mt-auto px-4 relative z-10">
                    <div className="w-full h-12 bg-white/10 rounded-xl border border-white/10 flex items-center px-3 gap-2 backdrop-blur-sm">
                      <div className="w-6 h-6 bg-[#818CF8] rounded-full flex items-center justify-center text-[10px] font-bold shadow-inner">U</div>
                      <div className="flex flex-col">
                        <span className="text-xs font-bold leading-tight">User Account</span>
                        <span className="text-[9px] text-white/60">Free Plan</span>
                      </div>
                    </div>
                  </div>
                </motion.div>

                {/* Main Content - Restored Look + Animations */}
                <div className="flex-1 p-6 md:p-8 relative bg-[#F9FAFB] z-10 overflow-hidden">
                  {/* Environment Lighting Gradient */}
                  <div className="absolute top-0 left-0 w-full h-full bg-gradient-to-br from-indigo-50/10 to-transparent pointer-events-none" />
                  
                  {/* Data Particulates */}
                  <div className="absolute inset-0 z-0 pointer-events-none overflow-hidden text-left">
                    {mounted && particles.map((p, i) => (
                      <motion.div
                        key={i}
                        initial={{ opacity: 0, x: p.startX, y: p.startY }}
                        animate={{ 
                          opacity: [0, 0.4, 0],
                          y: [0, -40, 0],
                          x: [0, p.moveX, 0]
                        }}
                        transition={{ 
                          duration: p.duration, 
                          repeat: Infinity, 
                          delay: p.delay 
                        }}
                        className="absolute w-1 h-1 bg-indigo-400/40 rounded-full blur-[1px]"
                      />
                    ))}
                  </div>

                  <div className="flex justify-between items-center mb-6 relative z-30">
                    <h2 className="text-2xl font-extrabold text-zinc-900 tracking-tight">Database</h2>
                    <motion.div 
                      animate={{ opacity: [1, 0.6, 1], scale: [1, 1.02, 1] }}
                      transition={{ duration: 3, repeat: Infinity }}
                      className="bg-orange-50 text-orange-600 border border-orange-200 px-3 py-1 rounded-full text-xs font-bold flex items-center gap-1.5 shadow-sm hidden md:flex"
                    >
                      <div className="w-1.5 h-1.5 bg-orange-500 rounded-full animate-pulse" /> 15.77 MB used
                    </motion.div>
                  </div>
                  
                  <p className="text-sm text-zinc-500 mb-8 font-medium relative z-30">Follow the workflow: upload files, train your database, then use templates to generate focused linkedin posts.</p>

                  <div className="flex flex-wrap gap-3 mb-8 relative z-30">
                    <div className="bg-white border text-xs border-zinc-200 shadow-sm rounded-full px-3 py-1.5 text-zinc-600 font-bold flex items-center gap-1.5 shadow-indigo-100/10"><div className="w-2 h-2 bg-blue-500 rounded-full" /> 4 documents</div>
                    <div className="bg-white border text-xs border-zinc-200 shadow-sm rounded-full px-3 py-1.5 text-zinc-600 font-bold flex items-center gap-1.5 shadow-indigo-100/10"><div className="w-2 h-2 bg-emerald-500 rounded-full" /> 344 trained chunks</div>
                    <div className="bg-white border text-xs border-zinc-200 shadow-sm rounded-full px-3 py-1.5 text-zinc-600 font-bold flex items-center gap-1.5 hidden lg:flex shadow-indigo-100/10"><div className="w-2 h-2 bg-emerald-500 rounded-full" /> Completed • Queue: Healthy</div>
                  </div>

                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 relative z-30">
                    {/* Mockup Upload Box - Restored + Radar */}
                    <motion.div 
                      whileHover={{ y: -5, scale: 1.01, rotateX: 2 }}
                      className="bg-gradient-to-br from-[#818CF8] to-[#6E56CF] rounded-2xl p-6 shadow-xl text-center border border-[#A19CFF]/40 text-white relative overflow-hidden group/upload"
                    >
                      {/* Upload Radar Effect */}
                      <motion.div 
                        animate={{ rotate: 360 }}
                        transition={{ duration: 15, repeat: Infinity, ease: "linear" }}
                        className="absolute -top-1/2 -left-1/2 w-[200%] h-[200%] bg-gradient-to-r from-white/5 via-transparent to-transparent opacity-0 group-hover/upload:opacity-100 pointer-events-none"
                      />
                      
                      <motion.div 
                        animate={{ scale: [1, 1.1, 1], opacity: [0.2, 0.4, 0.2] }}
                        transition={{ duration: 4, repeat: Infinity }}
                        className="absolute -top-10 -right-10 w-40 h-40 bg-white rounded-full blur-3xl pointer-events-none" 
                      />

                      <div className="inline-block bg-white/20 px-3 py-1 text-[10px] uppercase tracking-widest font-bold rounded-full mb-3 backdrop-blur-sm border border-white/10 text-white shadow-sm relative z-10">Step 1 • Upload your source files</div>
                      <h3 className="text-xl md:text-2xl font-bold mb-1 tracking-tight relative z-10">Add files to your Database</h3>
                      <p className="text-[10px] md:text-xs text-indigo-100 mb-6 font-medium relative z-10">PDF or DOCX • max 50 MB each • indexed automatically</p>

                      <div className="border-2 border-dashed border-white/40 bg-black/10 rounded-xl p-5 md:p-6 hover:bg-black/20 transition-all cursor-pointer backdrop-blur-sm shadow-inner group-hover/upload:border-white/60 relative z-10">
                        <motion.div
                          animate={{ y: [0, -8, 0], rotate: [0, 4, 0, -4, 0] }}
                          transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
                        >
                          <FileText className="w-8 h-8 mx-auto mb-2 text-white" />
                        </motion.div>
                        <div className="font-bold text-sm mb-1 text-white">Drop files here</div>
                        <div className="text-[10px] md:text-xs text-indigo-100 mb-4 font-medium">or browse your computer</div>
                        <div className="bg-white text-[#6E56CF] text-xs font-bold px-4 py-2 rounded-lg shadow-md flex items-center justify-center gap-2 max-w-[150px] mx-auto hover:bg-zinc-50 transition-colors"><FileText className="w-3.5 h-3.5" /> Choose File</div>
                      </div>
                    </motion.div>

                    {/* Mockup Status Box - Restored + Spinner */}
                    <motion.div 
                      whileHover={{ y: -5, scale: 1.01, rotateX: 2 }}
                      className="bg-white rounded-2xl border border-zinc-200 shadow-xl p-6 flex flex-col relative overflow-hidden group/status"
                    >
                      <div className="absolute top-0 right-0 w-32 h-32 bg-emerald-500/5 rounded-full blur-2xl pointer-events-none" />
                      
                      <div className="inline-block text-[#6E56CF] bg-[#818CF8]/10 border border-[#818CF8]/20 px-3 py-1 text-[10px] uppercase tracking-widest font-bold rounded-full mb-4 self-start shadow-sm relative z-10">Step 2 • Verify training status</div>
                      <div className="text-[10px] uppercase font-bold text-zinc-400 mb-1 tracking-widest relative z-10">Database Status</div>
                      <h3 className="text-xl md:text-2xl font-bold text-zinc-900 mb-2 tracking-tight relative z-10">Training Complete</h3>
                      
                      <motion.div 
                        animate={{ 
                          scale: [1, 1.02, 1],
                          backgroundColor: ["rgba(236, 253, 245, 1)", "rgba(209, 250, 229, 1)", "rgba(236, 253, 245, 1)"]
                        }}
                        transition={{ duration: 2.5, repeat: Infinity }}
                        className="flex items-center gap-1.5 text-emerald-700 px-3 py-1.5 rounded-full w-max text-xs font-bold mb-1 border border-emerald-200 shadow-sm relative z-10"
                      >
                        {/* High-Tech Spinner */}
                        <div className="w-4 h-4 relative flex items-center justify-center">
                          <motion.div 
                            animate={{ rotate: 360 }}
                            transition={{ duration: 4, repeat: Infinity, ease: "linear" }}
                            className="absolute inset-0 border-2 border-emerald-300 border-t-emerald-600 rounded-full"
                          />
                          <CheckCircle2 className="w-2.5 h-2.5 relative z-10" />
                        </div>
                        All files indexed & ready
                      </motion.div>
                      
                      <div className="text-[10px] md:text-xs text-zinc-400 mb-6 font-medium mt-2 relative z-10">Last updated: 3s ago</div>

                      <div className="grid grid-cols-3 gap-3 mt-auto relative z-10">
                        {[
                          { val: "4", label: "Files", color: "text-blue-600" },
                          { val: "344", label: "Chunks", color: "text-emerald-600" },
                          { val: "4", label: "Trained", color: "text-amber-500" },
                        ].map((stat, i) => (
                          <motion.div 
                            key={i}
                            whileHover={{ 
                              y: -3, 
                              backgroundColor: "#F9FAFB",
                              boxShadow: "0 4px 12px rgba(0,0,0,0.05)"
                            }}
                            className="border border-zinc-100 rounded-xl p-3 text-center bg-zinc-50/50 flex flex-col items-center justify-center shadow-sm relative overflow-hidden group/stat transition-all"
                          >
                            {/* Shimmering Stat Effect */}
                            <motion.div 
                              animate={{ x: ["-100%", "200%"] }}
                              transition={{ duration: 3, repeat: Infinity, ease: "linear", delay: i * 0.8 }}
                              className="absolute inset-0 bg-gradient-to-r from-transparent via-white/50 to-transparent skew-x-12 opacity-0 group-hover/stat:opacity-100 pointer-events-none"
                            />
                            <motion.div 
                              animate={{ scale: [1, 1.15, 1] }} 
                              transition={{ duration: 4, repeat: Infinity, delay: i * 0.4 }}
                              className={`text-xl md:text-2xl font-black ${stat.color}`}
                            >
                              {stat.val}
                            </motion.div>
                            <div className="text-[8px] md:text-[9px] font-bold text-zinc-400 uppercase tracking-widest mt-0.5">{stat.label}</div>
                          </motion.div>
                        ))}
                      </div>
                    </motion.div>
                  </div>

                  {/* Real-time System Logs Ticker */}
                  <div className="mt-8 px-5 py-2.5 bg-zinc-900/[0.03] rounded-xl border border-zinc-200/50 flex items-center justify-between gap-4 relative z-30 overflow-hidden">
                    <div className="flex items-center gap-3 w-full">
                      <div className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse shrink-0" />
                      <div className="text-[9px] font-mono text-zinc-400 uppercase tracking-wider overflow-hidden whitespace-nowrap w-full">
                        <motion.div
                          animate={{ x: [0, -150, 0] }}
                          transition={{ duration: 25, repeat: Infinity, ease: "linear" }}
                          className="inline-block"
                        >
                          [SYS_LOG] INDUCTING SOURCE_04.PDF ... CALIBRATING SEMANTIC_MESH_V2 ... 344 CHUNKS GENERATED ... VECTOR_DB SYNC SUCCESS ... STATUS: STANDBY ...
                          <motion.span
                            animate={{ opacity: [1, 0, 1] }}
                            transition={{ duration: 0.8, repeat: Infinity, times: [0, 0.5, 1] }}
                            className="inline-block w-1.5 h-3 bg-zinc-400 align-middle ml-1"
                          />
                        </motion.div>
                      </div>
                    </div>
                    <div className="text-[8px] font-black text-zinc-300 tracking-tighter shrink-0 border-l border-zinc-200 pl-4 bg-[#F9FAFB]">BETA_ACCESS_V2</div>
                  </div>
                </div>
              </div>
            </div>
            {/* Glossy overlay effect for 3D realism */}
            <div className="absolute inset-0 rounded-2xl bg-gradient-to-tr from-transparent via-white/5 to-white/10 pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity duration-700 z-50" />
          </motion.div>
        </div>
      </section>

      {/* 2. Platform Statistics */}
      <section className="py-24 border-b border-zinc-200 bg-zinc-50 relative overflow-hidden">
        {/* Subtle background glow to blend with hero */}
        <motion.div 
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          transition={{ duration: 1.5 }}
          className="absolute top-0 left-1/2 -translate-x-1/2 w-full max-w-4xl h-48 bg-indigo-500/5 blur-[120px] pointer-events-none rounded-full" 
        />

        <div className="container mx-auto px-6 max-w-7xl relative z-10">
          <p className="text-center text-xs font-bold text-zinc-400 uppercase tracking-[0.2em] mb-16">
            The standard for scaling B2B inbound
          </p>

          <div className="flex flex-wrap items-start justify-center gap-10 md:gap-16 lg:gap-24">
            {[
              { value: 20000, suffix: "+", label: "Users Onboarded" },
              { value: 2.4, isDecimal: true, suffix: "M+", label: "Impressions Generated" },
              { value: 22, suffix: "+", label: "Avg. Posts / Month" },
              { value: 68, suffix: "%", label: "Report Higher Inbound" },
              { value: 4, label: "Minutes to First Draft" },
            ].map((item, i) => (
              <div key={i} className="flex flex-col items-center justify-start text-center max-w-[160px] relative group cursor-default">
                {/* Number */}
                <div className="text-4xl md:text-5xl font-extrabold mb-4 tracking-tighter text-zinc-900 transition-all duration-300 transform group-hover:-translate-y-1">
                  <span className="bg-clip-text group-hover:text-transparent group-hover:bg-gradient-to-r group-hover:from-[#818CF8] group-hover:to-[#6E56CF] transition-all duration-500">
                    <StatCounter value={item.value} isDecimal={item.isDecimal} suffix={item.suffix} />
                  </span>
                </div>
                {/* Expanding accent line */}
                <div className="h-0.5 w-6 bg-zinc-200 rounded-full mb-4 group-hover:w-12 group-hover:bg-[#818CF8] transition-all duration-500 ease-out" />
                {/* Label */}
                <div className="text-[10px] md:text-xs font-bold text-zinc-500 uppercase tracking-widest leading-relaxed px-2">
                  {item.label}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>
      
      {/* 2.5 Trusted By Logo Cloud */}
      <section className="py-16 bg-white border-b border-zinc-100 overflow-hidden relative">
        <div className="absolute inset-y-0 left-0 w-32 bg-gradient-to-r from-white to-transparent z-10" />
        <div className="absolute inset-y-0 right-0 w-32 bg-gradient-to-l from-white to-transparent z-10" />
        
        <div className="container mx-auto px-6 mb-10 text-center">
          <p className="text-[10px] font-bold text-zinc-400 uppercase tracking-[0.3em]">
            Scaling with forward-thinking teams
          </p>
        </div>

        <div className="flex w-[200%] gap-12 group">
          <motion.div 
            animate={{ x: ["0%", "-50%"] }}
            transition={{ duration: 30, repeat: Infinity, ease: "linear" }}
            className="flex gap-16 md:gap-24 items-center shrink-0 px-10"
          >
            {[
              "VERCEL", "STRIPE", "HUBSPOT", "NOTION", "AIRTABLE", "LINEAR", "FRAMER", "SLACK", "INTERCOM", "LOOM"
            ].map((logo) => (
              <span key={logo} className="text-2xl md:text-3xl font-black text-zinc-300 hover:text-indigo-600 transition-colors cursor-default tracking-tighter opacity-70">
                {logo}
              </span>
            ))}
          </motion.div>
          <motion.div 
            animate={{ x: ["0%", "-50%"] }}
            transition={{ duration: 30, repeat: Infinity, ease: "linear" }}
            className="flex gap-16 md:gap-24 items-center shrink-0 px-10"
          >
            {[
              "VERCEL", "STRIPE", "HUBSPOT", "NOTION", "AIRTABLE", "LINEAR", "FRAMER", "SLACK", "INTERCOM", "LOOM"
            ].map((logo) => (
              <span key={logo} className="text-2xl md:text-3xl font-black text-zinc-300 hover:text-indigo-600 transition-colors cursor-default tracking-tighter opacity-70">
                {logo}
              </span>
            ))}
          </motion.div>
        </div>
      </section>

      {/* 3. THE REAL PROBLEM (Combined Brutal Truth & Why Now) */}
      <section id="problem" className="py-32 bg-white relative overflow-hidden">
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#E1DFFC_1px,transparent_1px),linear-gradient(to_bottom,#E1DFFC_1px,transparent_1px)] bg-[size:40px_40px] opacity-[0.02] pointer-events-none" />
        <div className="container mx-auto px-6 max-w-7xl relative z-10">
          <div className="grid md:grid-cols-2 gap-12 lg:gap-24 items-stretch">
            
            {/* Left Column: Pain Points */}
            <div className="flex flex-col py-4">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-red-50 border border-red-100 text-[10px] font-bold tracking-[0.2em] uppercase text-red-600 mb-8 self-start shadow-sm">
                <Target className="w-3.5 h-3.5" /> The real problem
              </div>
              
              <h2 className="text-4xl md:text-6xl font-extrabold text-zinc-900 tracking-tighter leading-[1.1] mb-8">
                You&apos;re not lazy. <br />
                <span className="text-transparent bg-clip-text bg-gradient-to-r from-red-600 to-[#6E56CF]">Your system is broken.</span>
              </h2>
              
              <p className="text-xl text-zinc-500 font-medium leading-relaxed mb-12 max-w-xl">
                Every founder has insights worth sharing. The problem isn&apos;t ideas — it&apos;s the gap between what&apos;s in your head and what gets published.
              </p>
              
              <div className="space-y-4">
                {[
                  { 
                    title: "Hours lost to a blank page", 
                    desc: "You open LinkedIn, type three words, delete them, close the tab. Repeat next Tuesday." 
                  },
                  { 
                    title: "Generic AI that sounds like everyone else", 
                    desc: "ChatGPT posts get ignored. Your audience can smell templated content before they finish the first line." 
                  },
                  { 
                    title: "Your best ideas rotting in Notion docs", 
                    desc: "You have frameworks, case studies, hard-won lessons. They never make it to the feed." 
                  },
                  { 
                    title: "Inconsistency that kills momentum", 
                    desc: "You post once, get no traction, disappear for three weeks. The algorithm forgets you exist." 
                  }
                ].map((item, i) => (
                  <motion.div 
                    key={i}
                    initial={{ opacity: 0, x: -20 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.1 }}
                    viewport={{ once: true }}
                    className="p-6 bg-zinc-50 border border-zinc-100 rounded-2xl flex items-start gap-5 group hover:bg-white hover:border-red-100 hover:shadow-xl hover:shadow-red-900/5 transition-all duration-300"
                  >
                    <div className="w-10 h-10 rounded-xl bg-red-50 flex items-center justify-center shrink-0 border border-red-100 group-hover:bg-red-600 group-hover:text-white transition-colors">
                      <Target className="w-5 h-5 text-red-600 group-hover:text-white" />
                    </div>
                    <div>
                      <h4 className="font-bold text-zinc-900 mb-1">{item.title}</h4>
                      <p className="text-sm text-zinc-500 font-medium leading-relaxed">{item.desc}</p>
                    </div>
                  </motion.div>
                ))}
              </div>
            </div>

            {/* Right Column: Insight Card */}
            <motion.div 
              initial={{ opacity: 0, y: 40 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-100px" }}
              className="bg-indigo-50/40 border border-indigo-100 rounded-[3rem] p-8 md:p-14 relative overflow-hidden flex flex-col shadow-2xl shadow-indigo-900/5 group"
            >
              <div className="absolute top-0 right-0 w-64 h-64 bg-[#818CF8]/10 rounded-full blur-3xl pointer-events-none -translate-y-1/2 translate-x-1/2" />
              
              <div className="relative z-10 flex flex-col h-full">
                <blockquote className="mb-14">
                   <p className="text-2xl md:text-3xl font-serif text-indigo-900 leading-relaxed font-semibold">
                     Consistency is not optional — it is your unfair advantage <span className="text-transparent bg-clip-text bg-gradient-to-r from-red-600 to-[#6E56CF] italic font-sans font-black uppercase tracking-tighter ml-1">on LinkedIn.</span>
                   </p>
                </blockquote>
                
                <div className="grid grid-cols-2 gap-4 mb-14">
                  {[
                    { icon: "📱", stat: "1B+", desc: "Members globally. Largest professional active B2B audience." },
                    { icon: "📈", stat: "4×", desc: "Higher B2B conversion rate compared to all other overall networks." },
                    { icon: "👔", stat: "45M", desc: "Decision-makers actively engaging every single week." },
                    { icon: "🚀", stat: "561%", desc: "More reach from personal profiles vs company pages." }
                  ].map((s, i) => (
                    <div key={i} className="bg-white rounded-3xl p-6 border border-indigo-100 shadow-sm transform hover:-translate-y-1 transition-all duration-300">
                      <div className="text-xl mb-3">{s.icon}</div>
                      <div className="text-2xl md:text-4xl font-black text-indigo-900 tracking-tighter mb-2">
                        {s.stat}
                      </div>
                      <p className="text-[10px] text-zinc-500 font-bold leading-normal">
                        {s.desc}
                      </p>
                    </div>
                  ))}
                </div>

                <div className="p-6 rounded-2xl bg-white border border-indigo-100 border-l-4 border-l-red-500 mb-10 shadow-sm relative overflow-hidden">
                  <div className="absolute top-0 right-0 w-32 h-32 bg-red-500/5 rounded-full blur-2xl pointer-events-none" />
                  <p className="text-sm text-zinc-700 font-medium leading-relaxed relative z-10">
                    <span className="text-zinc-900 font-bold">The algorithm truth:</span> LinkedIn actively reduces distribution for profiles that post less than <span className="font-bold text-red-600">2× per week</span>.
                  </p>
                </div>
                
                <div className="space-y-6 mt-auto">
                  <h5 className="text-[10px] font-black uppercase tracking-[0.3em] text-indigo-600 mb-6">What goes wrong</h5>
                  {[
                    "Sporadic posting → algorithm deprioritises you",
                    "Generic content → zero engagement, zero trust",
                    "No publishing → competitors own your niche"
                  ].map((text, i) => (
                    <div key={i} className="flex items-center gap-4 text-zinc-800 font-bold text-sm md:text-base">
                      <div className="w-2.5 h-2.5 rounded-full bg-red-500 shrink-0 shadow-[0_0_12px_rgba(239,68,68,0.5)]" />
                      {text}
                    </div>
                  ))}
                </div>
              </div>
            </motion.div>

          </div>

          <div className="mt-20 flex justify-center">
            <Link 
              href="#how-it-works" 
              className="text-lg md:text-xl font-bold text-zinc-900 hover:text-[#6E56CF] transition-all flex items-center gap-2 group"
            >
              See how Velank fixes this <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
            </Link>
          </div>
        </div>
      </section>

      {/* 3. ENGINE ROOM (Scroll Spy) */}
      <section id="how-it-works" className="py-24 md:py-40 bg-[#FAFAFA] relative">
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute top-0 right-0 w-[800px] h-[800px] bg-indigo-50/50 rounded-full blur-[120px] -translate-y-1/2 translate-x-1/3" />
        </div>
        <div className="container mx-auto px-6 max-w-7xl relative z-10">
          <div className="text-center mb-20 md:mb-32">
            <div className="inline-flex justify-center mx-auto bg-indigo-50 px-4 py-2 rounded-full text-xs uppercase tracking-widest font-black text-indigo-600 mb-8 border border-indigo-100 shadow-sm">
              The Engine Room
            </div>
            <h2 className="text-4xl md:text-6xl lg:text-7xl font-extrabold mb-6 text-zinc-900 tracking-tight leading-[1.1]">
              A repeatable workflow <br className="hidden md:block" /> for generating <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-600 to-blue-500">inbound leads.</span>
            </h2>
            <p className="text-xl text-zinc-500 max-w-2xl mx-auto font-medium leading-relaxed">
              From raw fragmented knowledge sitting in your folders, to published undeniable authority on LinkedIn in 5 simple steps.
            </p>
          </div>

          <div className="flex flex-col md:flex-row gap-12 lg:gap-20 relative">
            {/* Left side: Scrolling Text Steps */}
            <div className="w-full md:w-[45%] lg:w-[40%] space-y-24 md:space-y-[60vh] py-10 md:py-20 pb-10 md:pb-[60vh]">
              {[
                { tag: "CORE DIFFERENTIATOR", title: "Posts Built From Your Brain, Not the Internet", desc: "Upload your case studies, decks, and documents. Every post Velank AI writes is pulled strictly from your real expertise — no hallucinated facts, no generic filler, no content that could have been written by anyone." },
                { tag: "YOUR VOICE", title: "One Document. Six Different Experts.", desc: "A founder, a consultant, and a sales lead can upload the exact same PDF and get three completely different posts — each one calibrated to their role, audience, and tone. Set it once. Sound like yourself, every time" },
                { tag: "UNIQUE CAPABILITY", title: "Turn Proven Viral Posts Into Your Own", desc: "Upload a swipe file of LinkedIn posts that went viral in your niche. Velank AI strips the structure, rebuilds it entirely in your voice, and grounds it in your knowledge. You get the format that works — with content that's unmistakably yours." },
                { tag: "NEVER GO SILENT", title: "A Month of Content. One Sunday Afternoon.", desc: "Most LinkedIn strategies die the moment life gets busy. Velank AI lets you bulk-schedule weeks of posts in a single session — published automatically at peak times, every week, whether you're in back-to-back meetings or on holiday." },
                { tag: "CLOSE THE LOOP", title: "Know It Will Land Before You Hit Publish.", desc: "Every draft gets readability scoring, tone analysis, and audience validation before it goes live. After publishing, track impressions, profile views, and engagement over time — so you always know what's working and can do more of it." }
              ].map((block, i) => (
                <div key={i} className={`workflow-step relative min-h-[30vh] flex flex-col justify-center transition-all duration-500 ${activeStep === i ? "opacity-100 scale-100 translate-x-0" : "opacity-30 scale-95 -translate-x-4"}`}>
                  <span className="text-6xl md:text-8xl font-black text-indigo-100 absolute -top-8 -left-6 tracking-tighter select-none z-0">0{i+1}</span>
                  <div className="relative z-10">
                    <div className="flex items-center gap-3 mb-6">
                      <div className={`w-12 h-1.5 rounded-full transition-colors duration-500 ${activeStep === i ? "bg-[#6E56CF]" : "bg-zinc-300"}`} />
                      <span className={`text-xs font-bold tracking-widest uppercase ${activeStep === i ? "text-[#6E56CF]" : "text-zinc-400"}`}>{block.tag}</span>
                    </div>
                    <h3 className="text-3xl lg:text-4xl font-bold mb-6 text-zinc-900 leading-tight">{block.title}</h3>
                    <p className="text-lg text-zinc-600 leading-relaxed font-medium">{block.desc}</p>
                  </div>
                </div>
              ))}
            </div>

            {/* Right side: Sticky Visual Container */}
            <div className="hidden md:block w-full md:w-[55%] lg:w-[60%] relative">
              <div className="sticky top-[10vh] h-[80vh] flex flex-col justify-center">
                <div className="w-full h-full max-h-[600px] bg-white rounded-[3rem] border border-zinc-200 shadow-[0_32px_80px_rgba(0,0,0,0.06)] relative overflow-hidden flex items-center justify-center p-10 bg-gradient-to-br from-white via-zinc-50/30 to-zinc-100/20 group">
                  <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-500/10 rounded-full blur-[80px] pointer-events-none transition-transform duration-700 group-hover:scale-125" />
                  <div className="absolute bottom-0 left-0 w-48 h-48 bg-emerald-500/5 rounded-full blur-[60px] pointer-events-none transition-transform duration-700 group-hover:scale-125" />

                  {/* Mockup Windows fading in via activeStep */}
                  <div className="relative w-full h-full flex items-center justify-center z-10">

                    {/* Step 1: Upload Knowledge */}
                    <div className={`w-full max-w-md absolute transition-all duration-700 ${activeStep === 0 ? "opacity-100 scale-100 translate-y-0" : "opacity-0 scale-95 translate-y-12 pointer-events-none"}`}>
                      <div className="bg-gradient-to-br from-[#818CF8] to-[#6E56CF] rounded-2xl p-8 shadow-2xl text-center text-white border border-[#A19CFF]/50 flex flex-col">
                        <div className="inline-flex justify-center mx-auto bg-white/20 px-4 py-1.5 rounded-full text-[10px] uppercase tracking-widest font-bold mb-6 border border-white/10">Step 1 • Provide Knowledge</div>
                        <h4 className="text-2xl font-bold mb-3">Sync Knowledge Sources</h4>

                        <div className="grid grid-cols-2 gap-4 mt-6 text-left">
                          <div className="bg-white/10 rounded-xl p-4 flex items-center gap-3 backdrop-blur-sm border border-white/20 hover:bg-white/20 transition-colors cursor-pointer">
                            <FileText className="w-5 h-5 text-blue-100" />
                            <span className="font-bold text-sm">PDF</span>
                          </div>
                          <div className="bg-white/10 rounded-xl p-4 flex items-center gap-3 backdrop-blur-sm border border-white/20 hover:bg-white/20 transition-colors cursor-pointer">
                            <FileText className="w-5 h-5 text-blue-100" />
                            <span className="font-bold text-sm">DOCX</span>
                          </div>
                        </div>
                        <div className="mt-8 border-2 border-dashed border-white/40 hover:border-white/60 rounded-xl p-8 bg-black/10 backdrop-blur-sm transition-colors cursor-pointer flex flex-col items-center">
                          <motion.div animate={{ y: [0, -5, 0] }} transition={{ duration: 2, repeat: Infinity }}>
                            <FileText className="w-10 h-10 mb-2 opacity-60" />
                          </motion.div>
                          <span className="text-sm font-bold opacity-60">Drop additional files here</span>
                        </div>
                      </div>
                    </div>

                    {/* Step 2: Role & Tone Calibration */}
                    <div className={`w-full max-w-md absolute transition-all duration-700 ${activeStep === 1 ? "opacity-100 scale-100 translate-y-0" : "opacity-0 scale-95 translate-y-12 pointer-events-none"}`}>
                      <div className="bg-white rounded-2xl p-8 shadow-[0_20px_50px_rgba(0,0,0,0.1)] border border-zinc-200 text-left flex flex-col">
                        <div className="flex items-center gap-3 mb-8">
                          <div className="w-10 h-10 rounded-xl bg-indigo-50 flex items-center justify-center border border-indigo-100">
                            <Sparkles className="w-5 h-5 text-indigo-600" />
                          </div>
                          <div className="font-bold text-zinc-900 text-xl tracking-tight">Voice Profiling</div>
                        </div>
                        <div className="space-y-4">
                          <div className="p-4 bg-indigo-50/50 border border-indigo-200 rounded-xl flex items-center justify-between">
                            <span className="text-sm font-bold text-indigo-900">Digital Twin Role</span>
                            <span className="text-xs font-black text-indigo-600 uppercase border border-indigo-200 px-2 py-0.5 rounded bg-white">SaaS Founder</span>
                          </div>
                          <div className="p-4 bg-zinc-50 border border-zinc-200 rounded-xl flex items-center justify-between">
                            <span className="text-sm font-bold text-zinc-700">Content Tone</span>
                            <span className="text-xs font-black text-zinc-500 uppercase border border-zinc-200 px-2 py-0.5 rounded bg-white">Authoritative</span>
                          </div>
                          <div className="p-4 bg-zinc-50 border border-zinc-200 rounded-xl flex items-center justify-between">
                            <span className="text-sm font-bold text-zinc-700">Writing Style</span>
                            <span className="text-xs font-black text-zinc-500 uppercase border border-zinc-200 px-2 py-0.5 rounded bg-white">First-Person</span>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Step 3: Drafting & Previews */}
                    <div className={`w-full max-w-md absolute transition-all duration-700 ${activeStep === 2 ? "opacity-100 scale-100 translate-y-0" : "opacity-0 scale-95 translate-y-12 pointer-events-none"}`}>
                      <div className="bg-white rounded-2xl p-8 shadow-[0_20px_50px_rgba(0,0,0,0.1)] border border-zinc-200 text-left flex flex-col">
                        <div className="bg-zinc-50 rounded-xl p-4 mb-6 border border-zinc-200">
                          <div className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-3">Live Drafting Context</div>
                          <div className="text-sm font-medium text-zinc-600 italic">&quot;Most startups fail because they solve a problem that doesn&apos;t exist...&quot;</div>
                        </div>
                        
                        <div className="space-y-4">
                          {["Educational", "Contrarian", "Case Study"].map((fw, i) => (
                            <div key={i} className={`p-4 rounded-xl border flex items-center justify-between transition-all ${i === 1 ? 'border-indigo-600 bg-indigo-50/50 shadow-sm scale-[1.02]' : 'border-zinc-100 bg-zinc-50 opacity-40'}`}>
                              <div className="flex items-center gap-3">
                                <div className={`w-2 h-2 rounded-full ${i === 1 ? 'bg-indigo-600 animate-pulse' : 'bg-zinc-300'}`} />
                                <span className={i === 1 ? 'font-bold text-indigo-700' : 'font-semibold text-zinc-600'}>{fw}</span>
                              </div>
                              {i === 1 && <CheckCircle2 className="w-5 h-5 text-indigo-600" />}
                            </div>
                          ))}
                        </div>

                        <button className="w-full mt-6 bg-gradient-to-r from-indigo-600 to-[#818CF8] text-white font-bold py-3.5 rounded-xl hover:shadow-lg transition-all shadow-indigo-200 flex items-center justify-center gap-2">
                           Rewrite With My Knowledge
                        </button>
                      </div>
                    </div>

                    {/* Step 4: Bulk Scheduling */}
                    <div className={`w-full max-w-md absolute transition-all duration-700 ${activeStep === 3 ? "opacity-100 scale-100 translate-y-0" : "opacity-0 scale-95 translate-y-12 pointer-events-none"}`}>
                      <div className="bg-white rounded-2xl p-8 shadow-[0_20px_50px_rgba(0,0,0,0.1)] border border-zinc-200 text-left flex flex-col">
                        <div className="flex justify-between items-center mb-8 border-b border-zinc-100 pb-5">
                          <div className="flex items-center gap-2.5">
                            <Clock className="w-6 h-6 text-[#6E56CF]" />
                            <div className="font-bold text-zinc-900 text-xl tracking-tight">Content Pipeline</div>
                          </div>
                          <div className="bg-emerald-50 text-emerald-600 border border-emerald-200 px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-widest flex items-center gap-1.5"><div className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse" />Live sync</div>
                        </div>

                        <div className="grid border border-zinc-200 rounded-xl overflow-hidden divide-y divide-zinc-200 bg-zinc-50 shadow-sm relative">
                          <div className="absolute top-0 right-0 w-12 h-full bg-gradient-to-l from-white/80 to-transparent pointer-events-none" />
                          <div className="p-4 flex items-center justify-between hover:bg-white transition-colors cursor-pointer group">
                            <div className="flex items-center gap-3">
                              <div className="w-2.5 h-2.5 rounded-sm bg-emerald-500 group-hover:scale-110 transition-transform" />
                              <div className="text-sm font-bold text-zinc-700">How we scaled by 300%</div>
                            </div>
                            <div className="text-[10px] font-bold text-zinc-400 uppercase">Today • 8:00 AM</div>
                          </div>
                          <div className="p-4 flex items-center justify-between hover:bg-white transition-colors cursor-pointer border-l-4 border-l-[#6E56CF] bg-white shadow-sm z-10 pr-2">
                            <div className="flex items-center gap-3 -ml-[1px]">
                              <div className="w-2.5 h-2.5 rounded-sm bg-amber-500 animate-pulse" />
                              <div className="text-sm font-bold text-[#6E56CF]">Contrarian DevOps view</div>
                            </div>
                            <div className="text-[9px] font-bold text-white uppercase bg-[#6E56CF] px-2 py-1 rounded shadow-sm relative z-20 shrink-0">Up Next</div>
                          </div>
                          <div className="p-4 flex items-center justify-between hover:bg-white transition-colors cursor-pointer group">
                            <div className="flex items-center gap-3">
                              <div className="w-2.5 h-2.5 rounded-sm bg-zinc-300 group-hover:bg-zinc-400 transition-colors" />
                              <div className="text-sm font-bold text-zinc-500 line-clamp-1">Weekly breakdown...</div>
                            </div>
                            <div className="text-[10px] font-bold text-zinc-400 uppercase mt-4">Draft</div>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Step 5: Readability & Close the Loop */}
                    <div className={`w-full max-w-md absolute transition-all duration-700 ${activeStep === 4 ? "opacity-100 scale-100 translate-y-0" : "opacity-0 scale-95 translate-y-12 pointer-events-none"}`}>
                      <div className="bg-white rounded-2xl p-8 shadow-[0_20px_50px_rgba(0,0,0,0.1)] border border-zinc-200 text-left flex flex-col">
                        <div className="flex justify-between items-center mb-6 border-b border-zinc-100 pb-4">
                          <div className="font-bold text-zinc-900 text-xl tracking-tight">Pre-Publish Analysis</div>
                          <BarChart3 className="w-5 h-5 text-[#6E56CF]" />
                        </div>

                        <div className="grid grid-cols-2 gap-4 mb-6">
                           <div className="bg-emerald-50 border border-emerald-100 rounded-xl p-4 flex flex-col items-center">
                             <div className="text-3xl font-black text-emerald-600 mb-1">92</div>
                             <div className="text-[9px] font-bold text-emerald-800 uppercase tracking-widest text-center">Readability<br/>Score</div>
                           </div>
                           <div className="bg-indigo-50 border border-indigo-100 rounded-xl p-4 flex flex-col items-center justify-center">
                             <div className="text-md font-bold text-indigo-600 mb-1">Authoritative</div>
                             <div className="text-[9px] font-bold text-indigo-400 uppercase tracking-widest">Tone Detected</div>
                           </div>
                        </div>

                        <div className="space-y-3">
                           <div className="flex justify-between items-center text-sm font-bold">
                             <span className="text-zinc-600">Hook Strength</span>
                             <span className="text-emerald-500 text-xs">Excellent (8/10)</span>
                           </div>
                           <div className="w-full bg-zinc-100 rounded-full h-1.5">
                             <div className="bg-emerald-500 h-1.5 rounded-full" style={{ width: '80%' }}></div>
                           </div>
                           
                           <div className="flex justify-between items-center text-sm font-bold mt-4">
                             <span className="text-zinc-600">Call-to-Action</span>
                             <span className="text-emerald-500 text-xs">Clear (10/10)</span>
                           </div>
                           <div className="w-full bg-zinc-100 rounded-full h-1.5">
                             <div className="bg-emerald-500 h-1.5 rounded-full" style={{ width: '100%' }}></div>
                           </div>
                        </div>

                      </div>
                    </div>

                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 5. ENGINE ROOM (How it works Overview) */}
      <section className="py-32 bg-white relative overflow-hidden">
        <div className="absolute top-0 right-0 w-[600px] h-[600px] bg-indigo-50 rounded-full blur-[150px] -translate-y-1/2 translate-x-1/2 opacity-60 pointer-events-none" />
        <div className="container mx-auto px-6 max-w-[1400px] relative z-10">
          <div className="mb-16">
            <h2 className="text-[10px] uppercase font-bold tracking-[0.2em] text-indigo-600 mb-6 font-bold uppercase">The Engine Room</h2>
            <h3 className="text-3xl md:text-5xl font-extrabold mb-6 tracking-tight text-zinc-900 leading-[1.1]">
              From knowledge to <br className="hidden md:block"/>
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#818CF8] to-[#6E56CF] italic font-serif">published authority</span>
            </h3>
            <p className="text-zinc-600 font-medium text-lg max-w-2xl">Four steps. First post live in under 10 minutes. No blank page. Ever.</p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 border border-zinc-200 rounded-3xl overflow-hidden divide-y md:divide-y-0 md:divide-x divide-zinc-200 text-left bg-zinc-50/50 shadow-sm">
            {[
              {
                num: "01", time: "⏱ ~3 min", title: "Upload what you already have",
                desc: "Drop in PDFs, Word docs, case studies, proposals, decks. Velank AI reads it, understands it, and builds your personal knowledge base. No writing required."
              },
              {
                num: "02", time: "⚡ 60 seconds", title: "Tell Velank AI who you are",
                desc: "Select your role, target audience, tone, goal, and post style. Every output is calibrated to speak directly to the right people in a voice that's unmistakably yours."
              },
              {
                num: "03", time: "⏱ ~3 min", title: "Get posts written and ready",
                desc: "Posts are grounded strictly in your uploaded knowledge. For every draft you'll see the hook strategy and engagement angle — so you know what you're approving before you approve it."
              },
              {
                num: "04", time: "⏱ ~2 min", title: "Approve and forget about it",
                desc: "One green light. Velank AI schedules and publishes at optimal times automatically. No copy-pasting. No manual posting. Your LinkedIn keeps growing while you focus on everything else."
              }
            ].map((s, i) => (
              <div key={i} className="p-10 hover:bg-white transition-colors group cursor-default">
                <div className="text-4xl lg:text-5xl font-extralight text-zinc-200 mb-6 font-serif group-hover:text-zinc-400 transition-colors">{s.num}</div>
                <div className="text-[10px] font-bold text-indigo-600 bg-indigo-50 border border-indigo-100 px-3 py-1.5 rounded-full inline-block tracking-widest uppercase mb-6">{s.time}</div>
                <h4 className="text-lg font-bold text-zinc-900 mb-4 leading-snug">{s.title}</h4>
                <p className="text-zinc-500 text-sm leading-relaxed font-medium">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      
{/* 6. Bento Grid Features / Core Value */}
      <section id="features" className="py-32 bg-zinc-50 border-t border-zinc-200 overflow-hidden relative">
        <div className="container mx-auto px-6 max-w-6xl">
          <div className="text-center mb-20">
            <h2 className="text-indigo-600 font-semibold tracking-wide uppercase text-sm mb-3">What Velank AI brings to the table</h2>
            <h3 className="text-4xl md:text-5xl font-bold mb-6 text-zinc-900 tracking-tight">Your Knowledge. Your Voice.<br />On LinkedIn — Every Single Week.</h3>
            <p className="text-zinc-600 text-xl max-w-2xl mx-auto leading-relaxed">
              Anyone can copy a prompt. Nobody can copy your expertise. Velank AI writes strictly from what you know — so your content stands out in a feed full of noise.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
            {/* Big Bento 1 */}
            <motion.div
              initial={{ opacity: 0, y: 40 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, ease: "easeOut" }}
              viewport={{ once: true, margin: "-50px" }}
              className="md:col-span-12 bg-zinc-50 rounded-3xl border border-zinc-200 p-8 md:p-12 relative overflow-hidden group shadow-sm hover:shadow-md transition-shadow"
            >
              <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-100 rounded-full blur-[80px] -translate-y-1/2 translate-x-1/2 group-hover:scale-110 transition-transform duration-700" />
              <div className="relative z-10 h-full flex flex-col justify-between">
                <div className="mb-12">
                  <div className="w-14 h-14 bg-indigo-100 rounded-xl flex items-center justify-center mb-6">
                    <FileText className="w-7 h-7 text-indigo-600" />
                  </div>
                  <h4 className="text-2xl md:text-3xl font-bold text-zinc-900 mb-4">Knowledge Base Engine</h4>
                  <p className="text-zinc-600 text-lg md:text-xl leading-relaxed font-bold mb-2">
                    Everything you know, finally put to work.
                  </p>
                  <p className="text-zinc-500 text-base leading-relaxed">
                    Upload your PDFs and Word documents — case studies, service decks, proposals, past wins. Velank AI securely indexes your material and uses it as the sole source for every post. No generic internet data. No invented facts. Just your real expertise, turned into content.
                  </p>
                </div>
                {/* Mini UI mockup */}
                <div className="w-full bg-white rounded-xl border border-zinc-200 shadow-sm p-5 flex flex-col mt-auto relative overflow-hidden">
                  <div className="absolute top-0 left-0 w-1.5 h-full bg-green-500 blur-[1px]"></div>
                  <div className="flex justify-between items-center mb-5 pl-4">
                    <div>
                      <div className="text-[10px] font-bold text-[#6E56CF] uppercase tracking-wider mb-1">Step 2 • Verify training status</div>
                      <h5 className="text-lg font-bold text-zinc-900 tracking-tight">Training Complete</h5>
                    </div>
                    <div className="hidden sm:flex items-center gap-1.5 bg-green-50 border border-green-200 text-green-700 px-3 py-1.5 rounded-full text-xs font-bold shadow-sm">
                      <CheckCircle2 className="w-3.5 h-3.5" /> All files indexed & ready
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-3 pl-4">
                    <div className="border border-zinc-200 rounded-xl p-3 text-center bg-zinc-50/50 flex flex-col items-center justify-center">
                      <div className="text-2xl font-black text-[#6E56CF]">4</div>
                      <div className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest mt-1 text-center">Files</div>
                    </div>
                    <div className="border border-zinc-200 rounded-xl p-3 text-center bg-zinc-50/50 flex flex-col items-center justify-center">
                      <div className="text-2xl font-black text-emerald-600">344</div>
                      <div className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest mt-1 text-center whitespace-nowrap">Chunks</div>
                    </div>
                    <div className="border border-zinc-200 rounded-xl p-3 text-center bg-zinc-50/50 flex flex-col items-center justify-center">
                      <div className="text-2xl font-black text-amber-600">4</div>
                      <div className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest mt-1 text-center font-bold">Trained</div>
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>

            {/* Small Bento 1 */}
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.1, ease: "easeOut" }}
              viewport={{ once: true, margin: "-50px" }}
              className="md:col-span-6 bg-zinc-50 rounded-3xl border border-zinc-200 p-8 relative overflow-hidden shadow-sm hover:shadow-md transition-shadow"
            >
              <div className="w-14 h-14 bg-blue-100 rounded-xl flex items-center justify-center mb-6">
                <Clock className="w-7 h-7 text-blue-600" />
              </div>
              <h4 className="text-2xl font-bold text-zinc-900 mb-4">Consistency, Automated.</h4>
              <p className="text-zinc-600 text-lg leading-relaxed font-bold mb-2">
                Show up every week without thinking about it.
              </p>
              <p className="text-zinc-500 text-base leading-relaxed">
                Approve your drafts and Velank AI handles the rest — scheduled, published, and live at the right time. Automatically.
              </p>
              <div className="mt-8 bg-white border border-zinc-200 rounded-xl p-5 shadow-sm">
                <div className="flex items-center gap-2 mb-4">
                  <BarChart3 className="w-4 h-4 text-zinc-400" />
                  <h5 className="text-sm font-bold text-zinc-700">Optimal Posting Windows</h5>
                </div>
                <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 flex flex-col items-center justify-center text-center shadow-sm relative overflow-hidden group">
                  <div className="absolute top-0 right-0 w-16 h-16 bg-white/40 rounded-full blur-xl group-hover:scale-150 transition-transform" />
                  <span className="text-2xl mb-2 relative z-10">🌅</span>
                  <span className="font-bold text-emerald-800 text-base mb-1 relative z-10">8–10 AM</span>
                  <span className="text-[11px] font-medium text-emerald-600/80 relative z-10">Tue–Thu • Best reach</span>
                </div>
              </div>
            </motion.div>

            {/* Small Bento 2 */}
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.2, ease: "easeOut" }}
              viewport={{ once: true, margin: "-50px" }}
              className="md:col-span-6 bg-zinc-50 rounded-3xl border border-zinc-200 p-8 relative overflow-hidden shadow-sm hover:shadow-md transition-shadow"
            >
              <div className="w-14 h-14 bg-green-100 rounded-xl flex items-center justify-center mb-6">
                <BarChart3 className="w-7 h-7 text-green-600" />
              </div>
              <h4 className="text-2xl font-bold text-zinc-900 mb-4">Measurable Impact.</h4>
              <p className="text-zinc-600 text-lg leading-relaxed font-bold mb-2">
                See exactly what your content is doing for your pipeline.
              </p>
              <p className="text-zinc-500 text-base leading-relaxed">
                Track impressions, profile views, and inbound DMs — all tied directly to your content. Know what&apos;s working, double down on it, and watch your LinkedIn turn from a static profile into an active lead source.
              </p>
              <div className="mt-8 flex items-end gap-2 h-20">
                {[40, 60, 45, 80, 100, 75, 90].map((h, i) => (
                  <div key={i} className="flex-1 bg-green-500 rounded-t-sm" style={{ height: `${h}%` }} />
                ))}
              </div>
            </motion.div>

            {/* Big Bento 2 - Dark Mode Implementation */}
            <motion.div
              initial={{ opacity: 0, y: 40 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, delay: 0.3, ease: "easeOut" }}
              viewport={{ once: true, margin: "-50px" }}
              className="md:col-span-12 bg-zinc-900 rounded-3xl border border-zinc-800 p-8 md:p-12 relative overflow-hidden group shadow-2xl transition-all hover:bg-black"
            >
              <div className="absolute top-0 right-0 w-64 h-64 bg-[#6E56CF]/20 rounded-full blur-[80px] -translate-y-1/2 translate-x-1/2 group-hover:scale-110 transition-transform duration-700" />
              <div className="relative z-10 h-full flex flex-col justify-between">
                <div className="mb-8">
                  <div className="w-14 h-14 bg-[#6E56CF]/10 rounded-xl border border-white/5 flex items-center justify-center mb-6">
                    <Users className="w-7 h-7 text-[#818CF8]" />
                  </div>
                  <h4 className="text-2xl md:text-3xl font-bold text-white mb-4">One upload. Infinite angles.</h4>
                  <p className="text-zinc-300 text-lg md:text-xl leading-relaxed mb-4">
                    A founder, a consultant, a BDE, and a sales lead all have different audiences with different needs. Set your role, your industry, your tone, and your goal — and Velank AI generates posts that speak precisely to your world. Upload one document and get content that fits your context, not someone else&apos;s.
                  </p>
                  <p className="text-[#818CF8] text-sm md:text-base font-bold uppercase tracking-widest">
                    Works for every industry — SaaS, consulting, finance, crypto, agencies, and beyond.
                  </p>
                </div>
                <div className="w-full bg-zinc-800/50 rounded-2xl border border-white/5 p-6 mt-auto shadow-sm relative overflow-hidden backdrop-blur-md">
                  <div className="absolute top-0 right-0 w-32 h-32 bg-[#6E56CF]/10 blur-[50px] pointer-events-none" />
                  <div className="flex items-center gap-3 mb-6 relative z-10">
                    <div className="w-6 h-6 rounded bg-gradient-to-b from-[#818CF8] to-[#6E56CF] flex items-center justify-center text-xs font-bold text-white shadow-sm border border-white/20">1</div>
                    <span className="text-sm font-bold text-white uppercase tracking-widest text-[10px]">Target Audience Profile</span>
                  </div>
                  <div className="grid grid-cols-2 gap-3 mb-3 relative z-10">
                    <div className="bg-zinc-900 border-2 border-[#6E56CF] rounded-xl p-3 flex items-center justify-between shadow-lg">
                      <div className="flex items-center gap-3">
                        <LayoutDashboard className="w-4 h-4 text-[#818CF8]" />
                        <div className="text-left">
                          <div className="text-xs font-bold text-white">Crypto Focus</div>
                          <div className="text-[10px] text-[#818CF8] font-bold">Blockchain & Web3</div>
                        </div>
                      </div>
                      <CheckCircle2 className="w-4 h-4 text-[#6E56CF]" />
                    </div>
                    <div className="bg-zinc-800/80 border border-white/5 rounded-xl p-3 flex items-center gap-3 opacity-40">
                      <TrendingUp className="w-4 h-4 text-zinc-500" />
                      <div className="text-left">
                        <div className="text-xs font-bold text-zinc-500">SaaS Growth</div>
                        <div className="text-[10px] text-zinc-500">HubSpot/Salesforce</div>
                      </div>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-3 relative z-10">
                    <div className="bg-zinc-900 border-2 border-[#6E56CF] rounded-xl p-3 flex items-center justify-between shadow-lg">
                      <div className="flex items-center gap-3">
                        <Users className="w-4 h-4 text-[#818CF8]" />
                        <div className="text-left">
                          <div className="text-xs font-bold text-white">Product Leader</div>
                          <div className="text-[10px] text-[#818CF8] font-bold">Strategy & Vision</div>
                        </div>
                      </div>
                      <CheckCircle2 className="w-4 h-4 text-[#6E56CF]" />
                    </div>
                    <div className="bg-zinc-800/80 border border-white/5 rounded-xl p-3 flex items-center gap-3 opacity-40">
                      <Code2 className="w-4 h-4 text-zinc-500" />
                      <div className="text-left">
                        <div className="text-xs font-bold text-zinc-500">CTO Perspective</div>
                        <div className="text-[10px] text-zinc-500">Engineering culture</div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>
          </div>
        </div>
      </section>
{/* NEW: Interactive "Show Don't Tell" Output Comparison */}
      <section className="py-20 md:py-32 bg-white border-y border-zinc-100 relative overflow-hidden">
        <div className="absolute top-0 left-1/2 w-[800px] h-[800px] bg-indigo-50 rounded-full blur-[120px] pointer-events-none -translate-x-1/2 -translate-y-1/2" />

        <div className="container mx-auto px-6 max-w-5xl relative z-10">
          <div className="text-center mb-16">
            <h2 className="text-indigo-600 font-semibold tracking-wide uppercase text-sm mb-3">The Velank Difference</h2>
            <h3 className="text-4xl md:text-5xl font-bold mb-6 text-zinc-900 tracking-tight">Real Expertise vs. AI Generic</h3>
            <p className="text-zinc-600 text-xl max-w-2xl mx-auto leading-relaxed">
              Drag the slider to see how standard AI output compares to Velank AI&apos;s strictly knowledge-grounded posts.
            </p>
          </div>

          {/* Interactive Slider Container */}
          <div
            className="w-full h-[500px] md:h-[500px] bg-zinc-50 rounded-3xl border border-zinc-200 shadow-2xl overflow-hidden relative select-none cursor-ew-resize group"
            onMouseMove={(e) => {
              const rect = e.currentTarget.getBoundingClientRect();
              const percent = ((e.clientX - rect.left) / rect.width) * 100;
              setSliderPos(Math.min(Math.max(percent, 0), 100));
            }}
            onTouchMove={(e) => {
              const rect = e.currentTarget.getBoundingClientRect();
              const percent = ((e.touches[0].clientX - rect.left) / rect.width) * 100;
              setSliderPos(Math.min(Math.max(percent, 0), 100));
            }}
          >
            {/* Left Side: Generic AI - Dark Implementation */}
            <div className="absolute inset-0 bg-zinc-900 p-6 md:p-12 w-full h-full flex flex-col justify-center">
              <div className="flex items-center gap-3 mb-6">
                <div className="bg-zinc-800 text-red-500 p-2 rounded-lg border border-red-900/50 shadow-inner">
                  <Code2 className="w-5 h-5" />
                </div>
                <h4 className="font-bold text-white text-xl">Standard ChatGPT Output</h4>
              </div>
              <div className="space-y-4 max-w-md">
                <p className="text-zinc-400 font-bold">🚀 5 SECRETS to B2B SaaS Growth! 🚀</p>
                <p className="text-zinc-500 font-medium leading-relaxed">In today&apos;s fast-paced digital landscape, innovation is key. Are you struggling to increase your business revenue? Look no further! The secret to success in modern SaaS is simply to focus on customer centricity and leveraging synergistic paradigms.</p>
                <p className="text-zinc-500 font-medium leading-relaxed italic border-l-2 border-red-900/50 pl-4 py-1.5">&quot;Let&apos;s paradigm shift together! 👇 Comment &apos;GROWTH&apos; below to learn more.&quot;</p>
                <div className="flex gap-2 font-bold text-red-400 text-[10px] mt-4 uppercase tracking-widest">
                  <span className="bg-red-950/30 px-3 py-1 rounded-md border border-red-900/50">Cliche hooks</span>
                  <span className="bg-red-950/30 px-3 py-1 rounded-md border border-red-900/50">Zero actual insight</span>
                </div>
              </div>
            </div>

            {/* Right Side: Velank AI Output (Clipped) - Updated Brand Color */}
            <div
              className="absolute inset-0 bg-brand-mesh p-6 md:p-12 w-full h-full flex flex-col justify-center border-l-2 border-white/20"
              style={{ clipPath: `polygon(${sliderPos}% 0, 100% 0, 100% 100%, ${sliderPos}% 100%)` }}
            >
              <div className="flex items-center gap-3 mb-6 max-w-[280px] sm:max-w-md ml-auto md:ml-[50%] lg:ml-[25%] opacity-100 transition-opacity">
                <div className="bg-white text-[#6E56CF] p-2 rounded-lg shadow-xl">
                  <Sparkles className="w-5 h-5" />
                </div>
                <h4 className="font-bold text-white text-xl">Velank AI Output</h4>
              </div>
              <div className="space-y-4 max-w-[280px] sm:max-w-md ml-auto md:ml-[50%] lg:ml-[25%]">
                <p className="text-white font-bold leading-relaxed text-xl">Most founders measure CAC. Few measure &apos;Time-to-Trust&apos;.</p>
                <p className="text-white/80 font-medium leading-relaxed">In Q3, we noticed our enterprise sales cycle dropped from 94 days to just 41 days. We didn&apos;t change the product. We just stopped sending cold emails and started publishing our internal deployment frameworks.</p>
                <p className="text-white/80 font-medium leading-relaxed">When the buyer already understands your architecture before the demo, you skip the pitch and go straight to integration.</p>
                <div className="flex gap-2 font-bold text-white text-[10px] mt-4 uppercase tracking-widest">
                  <span className="bg-white/10 px-3 py-1 rounded-md border border-white/20 backdrop-blur-md">Grounded in data</span>
                  <span className="bg-white/10 px-3 py-1 rounded-md border border-white/20 backdrop-blur-md">Premium Authority Tone</span>
                </div>
              </div>
            </div>

            {/* Drag Handle */}
            <div
              className="absolute top-0 bottom-0 w-1 bg-white cursor-ew-resize flex items-center justify-center pointer-events-none shadow-[0_0_20px_rgba(255,255,255,0.5)] z-30"
              style={{ left: `${sliderPos}%` }}
            >
              <div className="w-10 h-10 bg-white rounded-full shadow-2xl flex items-center justify-center border-2 border-brand-purple transform -translate-x-1/2">
                <div className="flex gap-1">
                  <div className="w-1 h-3 bg-brand-violet/50 rounded-full" />
                  <div className="w-1 h-3 bg-brand-violet/50 rounded-full" />
                </div>
              </div>
            </div>
          </div>

          {/* Ghost CTA Section */}
          <div className="mt-16 flex justify-center">
            <Link 
              href="#preview" 
              className="inline-flex items-center gap-2.5 px-8 py-4 rounded-2xl border-2 border-zinc-200 text-zinc-600 hover:text-indigo-600 hover:border-indigo-200 hover:bg-indigo-50/50 transition-all font-bold group active:scale-95 shadow-sm"
            >
              Try it with your own content <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </Link>
          </div>
        </div>
      </section>

      <section className="py-32 bg-white border-t border-zinc-100 text-zinc-900 relative overflow-hidden">
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#E1DFFC_1px,transparent_1px),linear-gradient(to_bottom,#E1DFFC_1px,transparent_1px)] bg-[size:40px_40px] opacity-[0.02] pointer-events-none" />
        <div className="absolute top-1/2 right-0 w-[600px] h-[600px] bg-indigo-50 rounded-full blur-[150px] pointer-events-none -translate-y-1/2 translate-x-1/2" />

        <div className="container mx-auto px-6 max-w-7xl relative z-10">
          <div className="text-center mb-24 relative">
            <div className="inline-flex items-center justify-center gap-2 mb-6">
              <span className="h-px w-8 bg-zinc-200" />
              <h2 className="text-indigo-600 font-black tracking-widest uppercase text-xs">Velank AI vs Everything Else</h2>
              <span className="h-px w-8 bg-zinc-200" />
            </div>
            <h3 className="text-4xl md:text-6xl font-extrabold mb-8 tracking-tight leading-[1.1] text-zinc-900">
              You&apos;ve tried ChatGPT for LinkedIn. <span className="text-zinc-300 italic">You know why it doesn&apos;t work.</span>
            </h3>
            <p className="text-xl text-zinc-600 max-w-2xl mx-auto font-medium">
              Generic prompts produce generic posts. Velank AI is built from the ground up to make you sound like an elite industry leader, not a bot.
            </p>
          </div>

          <div className="flex flex-col lg:flex-row gap-6 max-w-6xl mx-auto">
            {/* Generic AI Tools */}
            <div className="w-full lg:w-1/2 bg-zinc-50 border border-zinc-200 rounded-[2rem] p-6 sm:p-8 md:p-12 relative overflow-hidden group">
              <div className="absolute top-0 inset-x-0 h-1 bg-gradient-to-r from-red-500/10 to-orange-500/10" />
              <div className="mb-10 flex items-center gap-4">
                <div className="w-12 h-12 bg-white rounded-xl flex items-center justify-center border border-zinc-200 shadow-sm">
                  <span className="text-red-500 font-bold text-xl">✗</span>
                </div>
                <div>
                  <h4 className="text-2xl font-bold text-zinc-900">Generic AI Tools</h4>
                  <p className="text-zinc-500 text-sm font-bold uppercase tracking-widest text-[10px]">ChatGPT, Claude, etc.</p>
                </div>
              </div>

              <div className="space-y-6">
                {[
                  { title: "No Memory of You", desc: "Knows nothing about you, your business, or your industry. Every session starts from zero — and it shows in the output." },
                  { title: "Sounds Like Everyone Else", desc: "Generic, hollow, forgettable. The same robotic tone that makes your audience scroll past." },
                  { title: "Manual Everything", desc: "Write in one tool, edit in another, schedule in a third. A tedious copy-paste workflow." },
                  { title: "Prompting is a Full-Time Job", desc: "Getting decent output means writing essays. And even then, the formatting is wrong and the tone is off." }
                ].map((item, i) => (
                  <div key={i} className="flex gap-4 p-5 rounded-2xl bg-white border border-zinc-100 shadow-sm group-hover:border-red-100 transition-colors">
                    <span className="text-red-500 mt-1 font-bold">✗</span>
                    <div>
                      <h5 className="font-bold text-zinc-900 mb-1">{item.title}</h5>
                      <p className="text-sm font-medium text-zinc-500">{item.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* The Velank Way - Updated Brand Colors */}
            <div className="w-full lg:w-1/2 bg-brand-mesh border border-white/20 rounded-[2rem] p-6 sm:p-8 md:p-12 relative overflow-hidden shadow-2xl shadow-[#6E56CF]/20 group">
              <div className="absolute top-0 inset-x-0 h-1 bg-white/20" />
              <div className="absolute -top-32 -right-32 w-64 h-64 bg-white/10 rounded-full blur-[60px] pointer-events-none" />

              <div className="mb-10 flex items-center gap-4 relative z-10">
                <div className="w-12 h-12 bg-white rounded-xl flex items-center justify-center shadow-lg">
                  <Sparkles className="w-6 h-6 text-[#6E56CF]" />
                </div>
                <div>
                  <h4 className="text-2xl font-bold text-white">Velank AI System</h4>
                  <p className="text-indigo-100 text-sm font-bold uppercase tracking-widest text-[10px]">The Authority Engine</p>
                </div>
              </div>

              <div className="space-y-6 relative z-10">
                {[
                  { title: "Data Grounding", desc: "Every post is written strictly from what you upload — your real expertise, your actual wins, your genuine insights." },
                  { title: "Nuanced Alignment", desc: "Your tone, your style, your vocabulary. Whether you're sharp and direct or warm and conversational." },
                  { title: "Integrated Engine", desc: "Write, approve, schedule, and publish — all in one place. No switching tabs, no copy-pasting." },
                  { title: "Works in Minutes", desc: "Upload your files and your first post is ready before your next meeting. No learning curve." }
                ].map((item, i) => (
                  <div key={i} className="flex gap-4 p-5 rounded-2xl bg-white/10 border border-white/20 shadow-inner group-hover:bg-white/15 transition-colors">
                    <CheckCircle2 className="w-5 h-5 text-white mt-1 shrink-0" />
                    <div>
                      <h5 className="font-bold text-white mb-1">{item.title}</h5>
                      <p className="text-sm font-medium text-indigo-100/90">{item.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 6. Wall Of Love (Testimonials) */}
      <WallOfLove />

      {/* NEW: Soft CTA - Interactive Post Preview */}
      <section id="preview" className="py-32 bg-brand-deep relative overflow-hidden group">
        <div className="absolute inset-0 bg-brand-mesh opacity-20" />
        <div className="absolute top-0 right-0 w-[800px] h-[800px] bg-white/10 rounded-full blur-[120px] -translate-y-1/2 translate-x-1/2" />
        
        <div className="container mx-auto px-6 max-w-6xl relative z-10 text-center">
          <div className="max-w-3xl mx-auto mb-16">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/10 border border-white/20 text-[10px] font-bold tracking-[0.2em] uppercase text-white mb-8 shadow-sm">
              <Sparkles className="w-3.5 h-3.5" /> Instant Authority
            </div>
            <h2 className="text-4xl md:text-6xl font-extrabold tracking-tight mb-8 text-white leading-[1.1]">
              See what Velank AI can <br className="hidden md:block"/> write for you in seconds.
            </h2>
            <p className="text-xl text-indigo-100/80 font-medium leading-relaxed">
              Drop your expertise once, and we&apos;ll show you exactly how we turn it into high-engagement content. No credit card required.
            </p>
          </div>

          <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-[3rem] p-4 md:p-8 flex flex-col md:flex-row gap-8 items-stretch">
            <div className="w-full md:w-1/2 bg-white rounded-[2.5rem] p-8 text-left flex flex-col justify-between shadow-2xl relative overflow-hidden">
              {isPreviewLoading && (
                <div className="absolute inset-0 bg-white/80 backdrop-blur-sm z-20 flex flex-col items-center justify-center p-8 text-center animate-in fade-in duration-500">
                  <div className="w-16 h-16 border-4 border-indigo-100 border-t-indigo-600 rounded-full animate-spin mb-6" />
                  <h5 className="text-xl font-bold text-zinc-900 mb-2">Analyzing Knowledge...</h5>
                  <p className="text-sm text-zinc-500 font-medium pb-20">Mapping your expertise to high-impact LinkedIn hook structures.</p>
                </div>
              )}
              <div>
                <div className="flex items-center gap-3 mb-8">
                  <div className="w-10 h-10 bg-indigo-50 rounded-xl flex items-center justify-center">
                    <LayoutDashboard className="w-5 h-5 text-indigo-600" />
                  </div>
                  <span className="font-bold text-zinc-900">Your Knowledge Source</span>
                </div>
                <div className="space-y-4">
                  <div className="p-4 bg-zinc-50 border border-zinc-100 rounded-xl text-sm font-medium text-zinc-600 line-clamp-3 italic">
                    &quot;Our Q4 strategy focuses on decentralizing the frontend layer using WASM modules to reduce latent compute costs by 40%. The main bottleneck is the cold-start time of legacy containers...&quot;
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="h-px flex-1 bg-zinc-100" />
                    <span className="text-[10px] text-zinc-400 font-bold uppercase tracking-widest">{isPreviewLoading ? "Processing" : "Ready to Analyze"}</span>
                    <div className="h-px flex-1 bg-zinc-100" />
                  </div>
                </div>
              </div>
              <button 
                onClick={() => {
                  setIsPreviewLoading(true);
                  setTimeout(() => {
                    setIsPreviewLoading(false);
                    setHasPreviewed(true);
                  }, 2500);
                }}
                disabled={isPreviewLoading || hasPreviewed}
                className="w-full mt-8 py-4 bg-zinc-900 text-white rounded-2xl font-black group hover:bg-black transition-all flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {hasPreviewed ? "Draft Generated" : "Generate My Preview"} <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </button>
            </div>

            <div className="w-full md:w-1/2 bg-indigo-50/50 rounded-[2.5rem] border border-indigo-100 p-8 text-left relative overflow-hidden">
              <div className="absolute top-0 right-0 px-4 py-1.5 bg-indigo-600 text-white text-[10px] font-black uppercase tracking-widest rounded-bl-2xl shadow-sm z-10 transition-transform duration-500">Velank AI Preview</div>
              
              <div className={`space-y-6 transition-all duration-1000 ${hasPreviewed ? 'opacity-100 blur-0 translate-y-0' : 'opacity-40 blur-sm translate-y-4'}`}>
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-white border border-indigo-100 flex items-center justify-center text-indigo-600 font-bold text-xs shadow-sm">M</div>
                  <div className="h-2 w-24 bg-indigo-200 rounded-full animate-pulse" />
                </div>
                {hasPreviewed ? (
                  <div className="space-y-4 animate-in slide-in-from-bottom-4 duration-700">
                    <p className="text-zinc-600 text-sm font-bold leading-relaxed">
                      WASM isn&apos;t just a performance optimization. It&apos;s a strategic moat.
                    </p>
                    <p className="text-zinc-500 text-xs leading-relaxed font-medium">
                      In Q4, we cut compute costs by 40% without touching the infra. How? We moved the logic to the edge...
                    </p>
                    <div className="h-px w-full bg-indigo-100 my-4" />
                    <div className="flex gap-2">
                       <span className="text-[9px] font-black text-indigo-600 bg-indigo-100 px-2 py-1 rounded">Strategy Hook</span>
                       <span className="text-[9px] font-black text-emerald-600 bg-emerald-100 px-2 py-1 rounded">High Retention</span>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-3">
                    <div className="h-4 w-full bg-white rounded-lg shadow-sm" />
                    <div className="h-4 w-[90%] bg-white rounded-lg shadow-sm" />
                    <div className="h-4 w-full bg-white rounded-lg shadow-sm" />
                    <div className="h-4 w-[75%] bg-white rounded-lg shadow-sm" />
                  </div>
                )}
                {!hasPreviewed && (
                  <div className="pt-4 flex gap-2">
                    <div className="h-6 w-20 bg-indigo-100 rounded-lg animate-pulse" />
                    <div className="h-6 w-24 bg-indigo-100 rounded-lg animate-pulse" />
                  </div>
                )}
              </div>
              
              <div className={`absolute inset-x-0 bottom-0 p-8 bg-gradient-to-t from-indigo-50 via-indigo-50/90 to-transparent flex flex-col items-center transition-all duration-700 ${hasPreviewed ? 'translate-y-0 opacity-100' : 'translate-y-10 opacity-0 pointer-events-none'}`}>
                 <p className="text-indigo-600 font-black text-sm mb-4">You have 5 drafts waiting.</p>
                 <Link href="https://app.velank.io/login" className="w-full py-4 bg-indigo-600 text-white rounded-xl font-bold text-center hover:bg-indigo-700 transition-all shadow-lg shadow-indigo-600/20 active:scale-95">
                   Claim All 5 Drafts
                 </Link>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 7. FAQ - Modern Bento Mitigation */}
      <section className="py-40 bg-zinc-50 border-t border-zinc-100 overflow-hidden">
        <div className="container mx-auto px-6 max-w-6xl relative z-10">
          <div className="text-center mb-24">
            <h2 className="text-4xl md:text-7xl font-black text-zinc-900 tracking-tighter mb-4 leading-[1]">Questions, <br /><span className="text-zinc-400">answered.</span></h2>
          </div>

          <div className="grid md:grid-cols-2 gap-4 lg:gap-6">
            {[
              { q: "Is there a learning curve?", a: "Not at all. We handle all orchestration under the hood. You simply upload your knowledge base, select your desired tone, and the system intelligently extracts insights." },
              { q: "Is my profile safe?", a: "Yes. Velank AI uses the official LinkedIn API via secure OAuth. We never ask for your password and publish purely within LinkedIn's compliance boundaries." },
              { q: "Is my data private?", a: "Your documents are encrypted and siloed. We never train our baseline models on your proprietary strategy. Your 'Digital Twin' belongs only to you." },
              { q: "Can I try before committing?", a: "Yes. We are currently offering a limited 30% discount for new members. Secure your price now to lock in your authority growth engine." },
            ].map((faq, i) => (
              <div key={i} className="p-10 bg-white border border-zinc-200 rounded-[2.5rem] shadow-sm hover:shadow-2xl hover:border-indigo-100 transition-all duration-500 group">
                <h4 className="text-xl md:text-2xl font-black text-zinc-900 mb-6 flex items-center gap-4">
                  <div className="w-10 h-10 rounded-2xl bg-indigo-50 flex items-center justify-center shrink-0 shadow-sm border border-indigo-100">
                    <HelpCircle className="w-5 h-5 text-indigo-600" />
                  </div>
                  {faq.q}
                </h4>
                <p className="text-zinc-500 text-lg leading-relaxed font-semibold pl-14">
                  {faq.a}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* NEW: ROI Teaser Section */}
      <section className="py-24 bg-zinc-50 border-t border-zinc-100 relative overflow-hidden">
        <div className="container mx-auto px-6 max-w-6xl relative z-10">
          <div className="bg-white border-2 border-indigo-100 rounded-[3rem] p-8 md:p-16 shadow-2xl relative overflow-hidden group text-zinc-900">
            <div className="absolute top-0 right-0 w-96 h-96 bg-indigo-50/50 rounded-full blur-[100px] pointer-events-none -translate-y-1/2 translate-x-1/3" />
            <div className="flex flex-col lg:flex-row items-center gap-12 relative z-10">
              <div className="lg:w-1/2 text-left">
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-50 border border-emerald-100 text-[10px] font-bold tracking-widest uppercase text-emerald-600 mb-6 shadow-sm">
                  <Calculator className="w-3.5 h-3.5" /> High-Intensity ROI
                </div>
                <h2 className="text-4xl md:text-5xl font-black text-zinc-900 mb-8 tracking-tight leading-tight">
                  Stop leaving money <br /> on the table.
                </h2>
                <p className="text-xl text-zinc-500 mb-10 font-medium leading-relaxed">
                  Most founders lose <span className="text-zinc-900 font-bold">$50k - $200k in pipeline</span> every year simply because they don&apos;t show up consistently on LinkedIn. See your real potential upside in 30 seconds.
                </p>
                <Link href="/tools/revenue-calculator" className="inline-flex items-center justify-center gap-2 px-8 py-4 bg-indigo-600 text-white rounded-2xl font-black text-lg shadow-xl hover:bg-indigo-700 transition-all group">
                  Calculate Your Authority ROI <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                </Link>
              </div>
              <div className="lg:w-1/2 w-full text-zinc-900">
                <div className="bg-zinc-50 rounded-3xl p-8 border border-zinc-100 shadow-inner relative overflow-hidden">
                  <div className="absolute top-0 right-0 p-4 bg-indigo-600 text-white text-[10px] font-black uppercase tracking-widest rounded-bl-xl shadow-md">Sample ROI</div>
                  <div className="space-y-6">
                    <div className="flex justify-between items-center border-b border-zinc-200 pb-4">
                      <span className="text-sm font-bold text-zinc-500">Avg Deal Value</span>
                      <span className="text-xl font-black text-zinc-900">$10,000</span>
                    </div>
                    <div className="flex justify-between items-center border-b border-zinc-200 pb-4">
                      <span className="text-sm font-bold text-zinc-500">Weekly Posts</span>
                      <span className="text-xl font-black text-zinc-900">3 Posts</span>
                    </div>
                    <div className="bg-indigo-600 rounded-2xl p-6 text-white shadow-lg">
                      <div className="text-[10px] font-bold uppercase tracking-widest opacity-80 mb-1">Potential Annual ROI</div>
                      <div className="text-4xl font-black text-white">$46,800 +</div>
                      <div className="text-[10px] font-medium opacity-70 mt-2">Based on current client benchmarks</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 8. Bottom CTA Band - Redesigned High-Impact Light Theme */}
      <section className="py-40 relative overflow-hidden bg-white border-t border-zinc-100">
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute top-0 right-0 w-full h-full bg-[linear-gradient(to_right,#E1DFFC_1px,transparent_1px),linear-gradient(to_bottom,#E1DFFC_1px,transparent_1px)] bg-[size:40px_40px] opacity-[0.02] pointer-events-none" />
          <div className="absolute bottom-0 left-1/4 w-[600px] h-[600px] bg-indigo-50 rounded-full blur-[150px] opacity-60" />
          <div className="absolute top-1/4 -right-1/4 w-[500px] h-[500px] bg-blue-50/50 rounded-full blur-[120px] opacity-40" />
        </div>

        <div className="container mx-auto px-6 relative z-10 max-w-5xl text-center">
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, ease: "easeOut" }}
            viewport={{ once: true }}
          >
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-50 border border-indigo-100 text-[10px] font-bold tracking-[0.2em] uppercase text-indigo-600 mb-8 shadow-sm">
              <Clock className="w-3.5 h-3.5" /> Stop the silence
            </div>

            <h2 className="text-4xl md:text-6xl lg:text-7xl font-extrabold tracking-tight mb-8 text-zinc-900 leading-[1.1]">
              The best time to start <br className="hidden md:block" /> was six months ago.
            </h2>

            <div className="relative inline-block mb-10">
              <h3 className="text-3xl md:text-5xl font-black text-transparent bg-clip-text bg-gradient-to-r from-indigo-600 to-[#818CF8] italic">
                The second best time is now.
              </h3>
              <div className="absolute -bottom-2 left-0 w-full h-1.5 bg-indigo-600/10 rounded-full overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  whileInView={{ width: "100%" }}
                  transition={{ duration: 1, delay: 0.5 }}
                  className="h-full bg-indigo-600"
                />
              </div>
            </div>

            <p className="text-xl md:text-2xl text-zinc-600 mb-16 max-w-3xl mx-auto font-medium leading-relaxed">
              Every week you stay silent, someone in your space is posting, growing, and closing deals that should have been yours. Build your authority system today.
            </p>

            <div className="flex flex-col items-center gap-8">
              <MagneticButton>
                <Link href="/pricing#authority-pipeline" className="inline-flex items-center justify-center rounded-2xl font-black transition-all bg-brand-mesh text-white hover:opacity-90 h-16 md:h-20 px-8 md:px-12 text-lg md:text-2xl shadow-[0_20px_50px_rgba(106,85,225,0.3)] hover:shadow-[0_25px_60px_rgba(106,85,225,0.4)] transform active:scale-95 group">
                  Claim Your Presence Now <ArrowRight className="ml-3 w-5 h-5 md:w-6 md:h-6 group-hover:translate-x-2 transition-transform" />
                </Link>
              </MagneticButton>
              <p className="text-xs font-bold text-zinc-400 uppercase tracking-widest">
                Start for free • No credit card required
              </p>

              <div className="flex items-center gap-12 pt-16 border-t border-zinc-100 w-full max-w-2xl justify-center">
                <div className="flex flex-col items-center gap-2">
                  <div className="text-2xl font-black text-zinc-900">20k+</div>
                  <div className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest">Active Users</div>
                </div>
                <div className="w-px h-10 bg-zinc-100" />
                <div className="flex flex-col items-center gap-2">
                  <div className="text-2xl font-black text-zinc-900">4.8/5</div>
                  <div className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest">User Rating</div>
                </div>
                <div className="w-px h-10 bg-zinc-100" />
                <div className="flex flex-col items-center gap-2">
                  <div className="text-2xl font-black text-zinc-900">30% OFF</div> <div className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest">Limited Offer</div>
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* 8. Self-Audit Teaser (Lead Gen for /audit) */}
      <section className="py-24 bg-indigo-600 relative overflow-hidden">
        <div className="absolute inset-0 bg-brand-mesh opacity-20" />
        <div className="container mx-auto px-6 relative z-10 text-center text-white">
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            className="max-w-4xl mx-auto"
          >
            <h2 className="text-4xl md:text-6xl font-black tracking-tight mb-8">
              Is your LinkedIn profile <br className="hidden md:block" /> actually <span className="italic font-serif text-indigo-200 underline decoration-indigo-400 decoration-8 underline-offset-8">losing you money?</span>
            </h2>
            <p className="text-xl md:text-2xl text-indigo-100 mb-12 font-medium">
               Get a hard-hitting, 12-point authority audit (usually $19) for <span className="text-white font-bold underline">FREE</span> today. Stop guessing and start scaling.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link href="/audit" className="px-10 py-5 bg-white text-indigo-600 rounded-2xl font-black text-xl shadow-2xl hover:bg-zinc-50 transition-all flex items-center gap-2 group">
                Claim Your Free Audit <ArrowRight className="w-6 h-6 group-hover:translate-x-1 transition-transform" />
              </Link>
              <Link href="/tools/authority-quiz" className="px-10 py-5 bg-indigo-500/30 text-white border border-white/20 rounded-2xl font-bold text-xl hover:bg-indigo-500/40 transition-all">
                Take the 60s Quiz
              </Link>
            </div>
            <p className="mt-8 text-sm text-indigo-200 font-bold uppercase tracking-widest">
               12,482 Leaders Audited in 2026
            </p>
          </motion.div>
        </div>
      </section>

      {/* NEW: Floating Sticky Bottom CTA */}
      <div
        className={`fixed bottom-0 md:bottom-8 left-0 md:left-1/2 md:-translate-x-1/2 w-full md:w-auto z-50 transition-all duration-500 transform ${showStickyCTA ? "translate-y-0 opacity-100" : "translate-y-full md:translate-y-20 opacity-0"
          }`}
      >
        <div className="bg-white/70 backdrop-blur-xl border-t md:border border-zinc-200 md:rounded-2xl p-4 md:px-8 md:py-4 shadow-2xl flex flex-col md:flex-row items-center justify-between gap-4 md:gap-8 min-w-[300px]">
          <div className="hidden md:block">
            <h4 className="font-bold text-zinc-900 text-sm">Velank AI 2.0</h4>
            <p className="text-zinc-500 text-xs font-medium">Start turning knowledge into pipeline.</p>
          </div>
          <Link href="https://app.velank.io/login" className="w-full md:w-auto whitespace-nowrap inline-flex items-center justify-center rounded-xl font-bold transition-all focus:outline-none focus:ring-4 focus:ring-[#818CF8]/20 bg-gradient-to-b from-[#818CF8] to-[#6E56CF] text-white hover:from-[#9B8CFF] hover:to-[#7760EA] h-12 px-6 shadow-lg shadow-[#6E56CF]/30">
            Buy Now & Get 30% Off
          </Link>
        </div>
      </div>

      <Footer />
    </div>
  );
}
