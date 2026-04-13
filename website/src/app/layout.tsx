import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { ExitIntent } from "@/components/ui/ExitIntent";
import { SmoothScrolling } from "@/components/ui/SmoothScrolling";
import "./globals.css";
 
const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
 
export const metadata: Metadata = {
  title: "Velank AI | Turn Your Expertise Into Inbound Leads",
  description: "AI-powered LinkedIn content generation for founders, consultants, and B2B teams. Turn your knowledge base into original, on-brand content that drives revenue.",
  icons: {
    icon: "/icon.svg",
    apple: "/icon.svg",
  },
  openGraph: {
    title: "Velank AI | Turn Your Expertise Into Inbound Leads",
    description: "AI-powered LinkedIn content generation for founders, consultants, and B2B teams.",
    url: "https://velank.ai",
    siteName: "Velank AI",
    images: [{ url: "https://velank.io/velank-og-image.png", width: 1200, height: 630 }],
    locale: "en_US",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Velank AI | Turn Your Expertise Into Inbound Leads",
    description: "AI-powered LinkedIn content generation for founders, consultants, and B2B teams.",
    images: ["https://velank.io/velank-og-image.png"],
  },
};
 
export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${inter.variable} font-sans antialiased text-zinc-900 bg-zinc-50 overflow-x-hidden w-full relative`}>
        <SmoothScrolling>
          {children}
          <ExitIntent />
        </SmoothScrolling>
      </body>
    </html>
  );
}
