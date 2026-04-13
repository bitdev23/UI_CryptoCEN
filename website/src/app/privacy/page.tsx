"use client";

import { motion } from "framer-motion";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";

export default function PrivacyPolicy() {
  return (
    <div className="min-h-screen bg-white text-zinc-900 relative flex flex-col pt-28 font-sans">
      <Header />
      
      <main className="flex-1 container mx-auto px-6 py-20 max-w-4xl">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <h1 className="text-4xl md:text-5xl font-black mb-8 tracking-tight text-zinc-900">Privacy Policy</h1>
          <p className="text-sm text-zinc-500 mb-12">Last Updated: March 14, 2026</p>
          
          <div className="prose prose-zinc prose-lg max-w-none space-y-8 text-zinc-600 font-medium leading-relaxed">
            <section>
              <h2 className="text-2xl font-bold text-zinc-900 mb-4">1. Introduction</h2>
              <p>
                At Velank AI, we respect your privacy and are committed to protecting your personal data. This Privacy Policy will inform you as to how we look after your personal data when you visit our website (regardless of where you visit it from) and tell you about your privacy rights and how the law protects you.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-bold text-zinc-900 mb-4">2. The Data We Collect</h2>
              <p>
                Personal data, or personal information, means any information about an individual from which that person can be identified. We may collect, use, store and transfer different kinds of personal data about you which we have grouped together as follows:
              </p>
              <ul className="list-disc pl-6 space-y-2">
                <li><strong>Identity Data:</strong> includes first name, last name, username or similar identifier.</li>
                <li><strong>Contact Data:</strong> includes email address and telephone numbers.</li>
                <li><strong>Technical Data:</strong> includes internet protocol (IP) address, your login data, browser type and version, time zone setting and location, browser plug-in types and versions, operating system and platform.</li>
                <li><strong>Usage Data:</strong> includes information about how you use our website, products and services.</li>
              </ul>
            </section>

            <section>
              <h2 className="text-2xl font-bold text-zinc-900 mb-4">3. How We Use Your Knowledge Base</h2>
              <p>
                Velank AI allows you to upload proprietary documents to build your &quot;Digital Twin&quot; or knowledge base. 
                <strong> We do not use your private documents to train our global baseline models.</strong> 
                Your documents are encrypted at rest and in transit, and are only used to contextualize the AI generations for your specific account.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-bold text-zinc-900 mb-4">4. Cookies</h2>
              <p>
                We use cookies to distinguish you from other users of our website. This helps us to provide you with a good experience when you browse our website and also allows us to improve our site.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-bold text-zinc-900 mb-4">5. Your Legal Rights</h2>
              <p>
                Under certain circumstances, you have rights under data protection laws in relation to your personal data, including the right to request access, correction, erasure, restriction, transfer, or to object to processing.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-bold text-zinc-900 mb-4">6. Contact Us</h2>
              <p>
                If you have any questions about this Privacy Policy or our privacy practices, please contact us at: <a href="mailto:support@velank.ai" className="text-indigo-600 font-bold">support@velank.ai</a>
              </p>
            </section>
          </div>
        </motion.div>
      </main>

      <Footer />
    </div>
  );
}
