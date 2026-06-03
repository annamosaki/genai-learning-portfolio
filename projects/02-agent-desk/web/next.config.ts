import type { NextConfig } from "next";

const basePath = process.env.ZONE_BASE_PATH ?? "";
const deskApi = process.env.AGENT_DESK_API_URL ?? "http://localhost:8200";

const nextConfig: NextConfig = {
  basePath: basePath || undefined,
  assetPrefix: basePath || undefined,
  env: {
    NEXT_PUBLIC_ZONE_BASE_PATH: basePath,
    NEXT_PUBLIC_AGENT_DESK_API_URL: deskApi,
    NEXT_PUBLIC_PORTFOLIO_URL: process.env.NEXT_PUBLIC_PORTFOLIO_URL || "http://localhost:3000",
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${deskApi}/api/:path*`,
      },
    ];
  },
  poweredByHeader: false,
};

export default nextConfig;
