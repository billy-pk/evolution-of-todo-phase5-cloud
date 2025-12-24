import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Optimize for Vercel deployment
  output: 'standalone',

  // Ensure environment variables are available
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
  },

  // Optional: Disable ESLint during builds if it causes issues
  // Uncomment if you get ESLint errors during Vercel deployment
  // eslint: {
  //   ignoreDuringBuilds: true,
  // },

  // Optional: Disable TypeScript errors during build
  // Only use this temporarily while debugging
  // typescript: {
  //   ignoreBuildErrors: true,
  // },
};

export default nextConfig;
