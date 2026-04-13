import Link from "next/link";
import Image from "next/image";
import { ArrowRight } from "lucide-react";

export function Footer() {
  return (
    <footer className="border-t border-zinc-200 bg-white pt-20 pb-8 relative overflow-hidden">
      {/* Decorative gradient */}
      <div className="absolute top-0 right-0 w-1/3 h-64 bg-indigo-50/50 rounded-full blur-[100px] pointer-events-none" />
      
      <div className="container mx-auto px-6 relative z-10">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-12 mb-16">
          <div className="col-span-1 md:col-span-3">
            <Link href="/" className="flex items-center gap-2 group mb-4">
              <div className="h-10 relative w-44">
                <Image 
                  src="/velank-logo-dark.svg" 
                  alt="Velank AI" 
                  fill
                  className="object-contain object-left"
                />
              </div>
            </Link>
            <p className="text-zinc-500 mb-8 max-w-sm leading-relaxed text-sm">
              The smartest way to turn your internal expertise into high-converting outbound LinkedIn pipelines.
            </p>
            <div className="flex gap-4">
              <div className="w-9 h-9 rounded-full bg-zinc-100 flex items-center justify-center text-zinc-600 hover:text-indigo-600 hover:bg-indigo-50 transition-colors cursor-pointer shadow-sm border border-zinc-200">𝕏</div>
              <div className="w-9 h-9 rounded-full bg-zinc-100 flex items-center justify-center text-zinc-600 hover:text-indigo-600 hover:bg-indigo-50 transition-colors cursor-pointer shadow-sm border border-zinc-200">in</div>
              <div className="w-9 h-9 rounded-full bg-zinc-100 flex items-center justify-center text-zinc-600 hover:text-indigo-600 hover:bg-indigo-50 transition-colors cursor-pointer shadow-sm border border-zinc-200">yt</div>
            </div>
          </div>
          
          <div className="col-span-1 md:col-span-2">
            <h4 className="text-zinc-900 font-bold text-xs uppercase tracking-[0.2em] mb-6">Solutions</h4>
            <ul className="space-y-4">
              <li><Link href="/for/founders" className="text-zinc-500 hover:text-indigo-600 transition-colors text-sm font-medium">For Founders</Link></li>
              <li><Link href="/for/consultants" className="text-zinc-500 hover:text-indigo-600 transition-colors text-sm font-medium">For Consultants</Link></li>
              <li><Link href="/for/coaches" className="text-zinc-500 hover:text-indigo-600 transition-colors text-sm font-medium">For Coaches</Link></li>
              <li><Link href="/for/agencies" className="text-zinc-500 hover:text-indigo-600 transition-colors text-sm font-medium">For Agencies</Link></li>
              <li><Link href="/audit" className="text-indigo-600 hover:text-indigo-700 transition-colors text-[10px] font-black uppercase tracking-widest flex items-center gap-2">Free Audit <span className="bg-indigo-100 text-indigo-700 text-[9px] px-1.5 py-0.5 rounded font-black">PRO</span></Link></li>
            </ul>
          </div>
          
          <div className="col-span-1 md:col-span-2">
            <h4 className="text-zinc-900 font-bold text-xs uppercase tracking-[0.2em] mb-6">Free Tools</h4>
            <ul className="space-y-4">
              <li><Link href="/tools/headline-generator" className="text-zinc-500 hover:text-indigo-600 transition-colors text-sm font-medium">Headline Generator</Link></li>
              <li><Link href="/tools/post-previewer" className="text-zinc-500 hover:text-indigo-600 transition-colors text-sm font-medium">Post Previewer</Link></li>
              <li><Link href="/tools/hook-vault" className="text-zinc-500 hover:text-indigo-600 transition-colors text-sm font-medium">Hook Vault</Link></li>
              <li><Link href="/tools/profile-mockup" className="text-zinc-500 hover:text-indigo-600 transition-colors text-sm font-medium flex items-center gap-2">Billion-Dollar Profile <span className="bg-indigo-100 text-indigo-700 text-[9px] px-1.5 py-0.5 rounded font-black">Hot</span></Link></li>
              <li><Link href="/tools/authority-heatmap" className="text-zinc-500 hover:text-indigo-600 transition-colors text-sm font-medium flex items-center gap-2">Revenue Heatmap <span className="bg-red-100 text-red-700 text-[9px] px-1.5 py-0.5 rounded font-black">Scan</span></Link></li>
              <li><Link href="/tools/revenue-calculator" className="text-zinc-500 hover:text-indigo-600 transition-colors text-sm font-medium flex items-center gap-2">ROI Calculator <span className="bg-emerald-100 text-emerald-700 text-[8px] px-1.5 py-0.5 rounded font-black">$$$</span></Link></li>
              <li><Link href="/tools/authority-quiz" className="text-indigo-600 hover:text-indigo-700 transition-colors text-[10px] font-black uppercase tracking-widest flex items-center gap-2">Authority Quiz <span className="bg-indigo-100 text-indigo-700 text-[8px] px-1.5 py-0.5 rounded font-black">New</span></Link></li>
            </ul>
          </div>

          <div className="col-span-1 md:col-span-2">
            <h4 className="text-zinc-900 font-bold text-xs uppercase tracking-[0.2em] mb-6">Comparison</h4>
            <ul className="space-y-4">
              <li><Link href="/compare/taplio" className="text-zinc-500 hover:text-indigo-600 transition-colors text-sm font-medium">Velank vs Taplio</Link></li>
              <li><Link href="/compare/postwise" className="text-zinc-500 hover:text-indigo-600 transition-colors text-sm font-medium">Velank vs Postwise</Link></li>
              <li><Link href="/pricing" className="text-zinc-500 hover:text-indigo-600 transition-colors text-sm font-medium">Pricing & ROI</Link></li>
            </ul>
          </div>

          <div className="col-span-1 md:col-span-3">
             <h4 className="text-zinc-900 font-bold text-xs uppercase tracking-[0.2em] mb-6">Updates</h4>
             <p className="text-sm text-zinc-500 mb-4 font-medium">Join 20k+ leaders getting our weekly growth systems.</p>
             <form className="flex gap-2">
               <input type="email" placeholder="Email address" className="flex-1 rounded-xl border border-zinc-200 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 font-medium" />
               <button type="submit" className="bg-zinc-900 text-white rounded-xl px-4 py-2.5 hover:bg-black transition-colors flex items-center justify-center shadow-lg">
                 <ArrowRight className="w-4 h-4" />
               </button>
             </form>
          </div>
        </div>
        
        <div className="pt-8 border-t border-zinc-200/80 flex flex-col md:flex-row items-center justify-between">
          <p className="text-zinc-400 text-sm">© {new Date().getFullYear()} Velank AI. All rights reserved.</p>
          <div className="flex gap-6 mt-4 md:mt-0">
             <Link href="/privacy" className="text-zinc-400 hover:text-zinc-600 text-sm font-medium">Privacy Policy</Link>
             <Link href="/terms" className="text-zinc-400 hover:text-zinc-600 text-sm font-medium">Terms of Service</Link>
             <Link href="#" className="text-zinc-400 hover:text-zinc-600 text-sm font-medium">Security</Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
