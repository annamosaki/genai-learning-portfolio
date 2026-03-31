import type { NextConfig } from 'next';

const basePath = process.env.ZONE_BASE_PATH ?? "";
const labApi = process.env.LAB_API_URL ?? "http://localhost:8100";

export default {
  basePath: basePath || undefined,
  // Keep assetPrefix aligned with basePath so Multi Zone rewrites on :3000
  // serve chunks from the same origin path (/demos/llm-lab/_next/...).
  assetPrefix: basePath || undefined,
  env: {
    NEXT_PUBLIC_ZONE_BASE_PATH: basePath,
    NEXT_PUBLIC_PORTFOLIO_URL: process.env.NEXT_PUBLIC_PORTFOLIO_URL || "http://localhost:3000",
  },
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${labApi}/api/:path*` }];
  },
} satisfies NextConfig;