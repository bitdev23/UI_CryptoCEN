"use client";

import { useEffect } from "react";
import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import { CheckCircle2, ArrowRight } from "lucide-react";
import Link from "next/link";
import { Header } from "@/components/layout/Header";

function SuccessContent() {
  const searchParams = useSearchParams();
  const paymentId = searchParams.get("payment_id") || searchParams.get("session_id");
  const gateway = searchParams.get("gateway") || "stripe";

  useEffect(() => {
    // Here you would typically verify the payment on the backend
  }, [paymentId]);

  return (
    <div className="min-h-screen bg-zinc-50 flex flex-col items-center justify-center p-6">
      <Header />
      
      <motion.div 
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="bg-white p-12 rounded-[3rem] shadow-2xl border border-zinc-100 max-w-lg w-full text-center"
      >
        <div className="w-20 h-20 bg-emerald-100 rounded-3xl flex items-center justify-center mx-auto mb-8">
          <CheckCircle2 className="w-10 h-10 text-emerald-600" />
        </div>
        
        <h1 className="text-4xl font-black text-zinc-900 mb-4 tracking-tight">Payment Successful!</h1>
        <p className="text-zinc-600 mb-8 font-medium">
          Welcome to the Velank AI. Your account has been upgraded and your digital equity is being built as we speak.
        </p>
        
        <div className="bg-zinc-50 p-6 rounded-2xl mb-10 text-left">
          <div className="flex justify-between mb-2">
            <span className="text-zinc-400 text-sm font-bold uppercase tracking-widest">Gateway</span>
            <span className="text-zinc-900 font-bold capitalize">{gateway}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-zinc-400 text-sm font-bold uppercase tracking-widest">Reference</span>
            <span className="text-zinc-900 font-bold truncate max-w-[180px]">{paymentId || "Processing..."}</span>
          </div>
        </div>

        <Link href="https://app.velank.io/login" className="inline-flex items-center justify-center w-full bg-indigo-600 text-white h-16 rounded-2xl font-black text-lg hover:bg-indigo-700 transition-all shadow-xl shadow-indigo-100">
          Go to App Dashboard <ArrowRight className="ml-2 w-5 h-5" />
        </Link>
      </motion.div>
    </div>
  );
}

export default function SuccessPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-zinc-50 flex items-center justify-center">
        <div className="w-12 h-12 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
      </div>
    }>
      <SuccessContent />
    </Suspense>
  );
}
