import type { NextConfig } from "next";
import path from "path";

const lab = process.env.LLM_LAB_URL ?? "http://localhost:3100";
const desk = process.env.AGENT_DESK_URL ?? "http://localhost:3200";
const digest = process.env.RESEARCH_DIGEST_URL ?? "http://localhost:3300";

const nextConfig: NextConfig = {
  experimental: {
    externalDir: true,
    serverActions: {
      allowedOrigins: [
        "localhost:3000",
        "localhost:3100",
        "localhost:3200",
        "localhost:3300",
        "annamosaki.com",
        "www.annamosaki.com",
        "lab.annamosaki.com",
        "desk.annamosaki.com",
        "digest.annamosaki.com",
      ],
    },
  },
  turbopack: {
    resolveAlias: {
      "@content": path.resolve(__dirname, "../../content"),
    },
  },
  webpack: (config) => {
    config.resolve.alias = {
      ...config.resolve.alias,
      "@content": path.resolve(__dirname, "../../content"),
    };
    return config;
  },
  async rewrites() {
    return [
      {
        source: "/demos/llm-lab",
        destination: `${lab}/demos/llm-lab`,
      },
      {
        source: "/demos/llm-lab/:path*",
        destination: `${lab}/demos/llm-lab/:path*`,
      },
      {
        source: "/demos/agent-desk",
        destination: `${desk}/demos/agent-desk`,
      },
      {
        source: "/demos/agent-desk/:path*",
        destination: `${desk}/demos/agent-desk/:path*`,
      },
      {
        source: "/demos/research-digest",
        destination: `${digest}/demos/research-digest`,
      },
      {
        source: "/demos/research-digest/:path*",
        destination: `${digest}/demos/research-digest/:path*`,
      },
    ];
  },
};

export default nextConfig;
