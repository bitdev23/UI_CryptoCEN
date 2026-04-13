"use client";
 
import { motion, AnimatePresence } from "framer-motion";
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import { Menu, X, ChevronRight } from "lucide-react";
import { TopBanner } from "../ui/TopBanner";
import Link from "next/link";
import { useState, useEffect } from "react";
import Image from "next/image";

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
 
export function Header() {
  // const pathname = usePathname();
  const [scrolled, setScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
 
  const handleNavClick = () => {
    setMobileMenuOpen(false);
  };
 
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", onScroll);
    return () => window.removeEventListener("scroll", onScroll);
  }, []);
 
  // Sync body scroll lock
  useEffect(() => {
    if (mobileMenuOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "auto";
    }
  }, [mobileMenuOpen]);
 
  return (
    <header className="fixed top-0 left-0 right-0 z-[100] flex flex-col w-full pointer-events-none">
      <div className="pointer-events-auto w-full">
        <TopBanner />
      </div>
      
      <div className={cn(
        "w-full transition-all duration-300 pointer-events-auto border-b",
        scrolled || mobileMenuOpen
          ? "bg-white/95 backdrop-blur-xl border-zinc-200 shadow-sm py-3" 
          : "bg-white lg:bg-transparent border-transparent py-4"
      )}>
        <div className="w-full px-4 sm:px-6 flex items-center justify-between relative max-w-[1400px] mx-auto">
          <Link 
            href="/" 
            className="flex items-center gap-2 group shrink-0" 
            onClick={() => setMobileMenuOpen(false)}
          >
            <div className="h-8 sm:h-10 relative w-32 sm:w-40">
              <Image 
                src="/velank-logo-dark.svg" 
                alt="Velank AI" 
                fill
                className="object-contain object-left transition-all duration-300"
                priority
              />
            </div>
          </Link>
          
          {/* Desktop - lg and up */}
          <nav className="hidden lg:flex items-center gap-1 bg-zinc-50/80 backdrop-blur-md px-1.5 py-1.5 rounded-full border border-zinc-200 relative">
            {[
              { href: "/", label: "Home" },
              { href: "/#problem", label: "Problem" },
              { href: "/#why-linkedin", label: "Why LinkedIn" },
              { href: "/#how-it-works", label: "How it Works" },
              { href: "/#features", label: "Features" },
              { href: "/who-this-is-for", label: "Who This Is for" },
              { href: "/pricing", label: "Pricing" },
              { href: "/audit", label: "Free Audit" },
            ].map((item) => (
              <Link
                key={item.label}
                href={item.href}
                className="relative px-4 py-1.5 text-xs font-bold text-zinc-500 hover:text-zinc-900 transition-colors group"
              >
                <span className="relative z-10">{item.label}</span>
                <motion.div
                  className="absolute inset-0 bg-white rounded-full shadow-sm opacity-0 group-hover:opacity-100 transition-opacity"
                  layoutId="navHover"
                  transition={{ type: "spring", bounce: 0.2, duration: 0.6 }}
                />
              </Link>
            ))}
          </nav>
 
          <div className="flex items-center shrink-0">
            <Link href="https://app.velank.io/login" className="hidden lg:inline-flex items-center justify-center rounded-xl font-bold border-2 border-zinc-200 text-zinc-600 hover:bg-zinc-50 hover:border-zinc-300 h-10 px-6 text-xs transition-all active:scale-95 mr-4">
              Login
            </Link>
            <Link href="https://app.velank.io/login" className="hidden sm:inline-flex items-center justify-center rounded-xl font-bold bg-indigo-600 text-white h-10 px-6 text-xs shadow-md active:scale-95 transition-all hover:bg-indigo-700">
              Start Free
            </Link>

            {/* Mobile Menu Toggle - ULTIMATE FORCE RIGHT ALIGNED BUTTON */}
            <button 
              className="flex lg:hidden w-11 h-11 items-center justify-center text-white bg-indigo-600 rounded-xl focus:outline-none relative z-[200] shadow-xl active:scale-90 border border-indigo-500 ml-auto ml-4"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              aria-label="Toggle menu"
            >
              {mobileMenuOpen ? <X className="w-7 h-7" strokeWidth={3} /> : <Menu className="w-7 h-7" strokeWidth={3} />}
            </button>
          </div>
        </div>
      </div>
 
      {/* Mobile Menu Overlay */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <motion.div 
            initial={{ opacity: 0, x: "100%" }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: "100%" }}
            transition={{ type: "spring", damping: 30, stiffness: 300 }}
            className="fixed inset-0 z-[150] lg:hidden bg-white pointer-events-auto flex flex-col overflow-y-auto"
          >
            <div className="flex flex-col p-6 pt-32 pb-12 min-h-full">
              <div className="flex flex-col gap-1 w-full">
                {[
                   { href: "/", label: "Home" },
                   { href: "/#problem", label: "Problem" },
                   { href: "/#why-linkedin", label: "Why LinkedIn" },
                   { href: "/#how-it-works", label: "How it Works" },
                   { href: "/#features", label: "Features" },
                   { href: "/who-this-is-for", label: "Who This Is For" },
                   { href: "/pricing", label: "Pricing" },
                   { href: "/audit", label: "Free Audit" },
                ].map((link) => (
                  <Link 
                    key={link.href}
                    href={link.href} 
                    onClick={handleNavClick}
                    className="text-3xl sm:text-4xl font-black text-zinc-900 py-5 sm:py-6 border-b border-zinc-100 flex justify-between items-center active:bg-zinc-50 px-2 transition-colors rounded-xl"
                  >
                    {link.label}
                    <ChevronRight className="w-6 h-6 sm:w-8 sm:h-8 text-zinc-300" />
                  </Link>
                ))}
              </div>
              
              <div className="mt-12 flex flex-col gap-4">
                <Link href="https://app.velank.io/login" onClick={handleNavClick} className="w-full py-4 text-center font-bold text-zinc-500 border border-zinc-200 rounded-2xl active:bg-zinc-50">Log in</Link>
                <Link href="https://app.velank.io/login" onClick={handleNavClick} className="w-full py-6 bg-indigo-600 text-white rounded-2xl text-center font-black text-xl shadow-2xl active:scale-95 transition-transform">Sign Up Now</Link>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  );
}
