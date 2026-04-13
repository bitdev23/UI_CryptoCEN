import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'export',
  trailingSlash: true,
  // Required for static exports if you want to use Next.js Image Optimization
  images: {
    unoptimized: true,
  },
};

export default nextConfig;
