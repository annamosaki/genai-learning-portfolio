import type { NextConfig } from "next";

const basePath = process.env.ZONE_BASE_PATH ?? "";
const digestApi = process.env.RESEARCH_DIGEST_API_URL ?? "http://localhost:8300";

const nextConfig: NextConfig = {
  basePath: basePath || undefined,
  assetPrefix: basePath || undefined,
  // Local multi-zone / curl often hits 127.0.0.1 while Next binds to localhost.
  allowedDevOrigins: ["127.0.0.1", "localhost"],
  env: {
    NEXT_PUBLIC_ZONE_BASE_PATH: basePath,
    NEXT_PUBLIC_RESEARCH_DIGEST_API_URL: digestApi,
    NEXT_PUBLIC_PORTFOLIO_URL: process.env.NEXT_PUBLIC_PORTFOLIO_URL || "http://localhost:3000",
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${digestApi}/api/:path*`,
      },
    ];
  },
  poweredByHeader: false,
};

export default nextConfig;
