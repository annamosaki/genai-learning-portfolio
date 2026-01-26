"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

type ServiceStatus = "online" | "offline" | "unknown";

interface Service {
  name: string;
  url: string;
  healthEndpoint: string;
  description: string;
  port: number;
}

const services: Service[] = [
  {
    name: "Portfolio API",
    url: process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000",
    healthEndpoint: "/health",
    description: "Main portfolio FastAPI backend",
    port: 8000,
  },
  {
    name: "LLM Lab API",
    url: process.env.NEXT_PUBLIC_LAB_API_URL || "http://localhost:8100",
    healthEndpoint: "/health",
    description: "LLM experimentation API",
    port: 8100,
  },
  {
    name: "Agent Desk API",
    url: process.env.NEXT_PUBLIC_AGENT_DESK_API_URL || "http://localhost:8200",
    healthEndpoint: "/health",
    description: "Agent orchestration API",
    port: 8200,
  },
  {
    name: "Research Digest API",
    url: process.env.NEXT_PUBLIC_RESEARCH_DIGEST_API_URL || "http://localhost:8300",
    healthEndpoint: "/health",
    description: "ArXiv + RSS research digest API",
    port: 8300,
  },
  {
    name: "Yahoo Finance MCP",
    url: process.env.NEXT_PUBLIC_YFMCP_URL || "http://localhost:8211",
    healthEndpoint: "/health",
    description: "yfmcp — live market data via Model Context Protocol",
    port: 8211,
  },
  {
    name: "Edgar MCP Server",
    url: process.env.NEXT_PUBLIC_EDGAR_MCP_URL || "http://localhost:8210",
    healthEndpoint: "/health",
    description: "SEC filing data MCP server",
    port: 8210,
  },
];

export default function StatusPage() {
  const [statuses, setStatuses] = useState<Record<string, ServiceStatus>>(
    Object.fromEntries(services.map(s => [s.name, "unknown" as ServiceStatus]))
  );

  const checkServiceHealth = async (service: Service): Promise<ServiceStatus> => {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 3000);
      
      const response = await fetch(`${service.url}${service.healthEndpoint}`, {
        signal: controller.signal,
        mode: 'cors',
      });
      
      clearTimeout(timeoutId);
      return response.ok ? "online" : "offline";
    } catch (error) {
      return "offline";
    }
  };

  const checkAllServices = async () => {
    const checks = await Promise.all(
      services.map(async (service) => ({
        name: service.name,
        status: await checkServiceHealth(service),
      }))
    );
    
    setStatuses(Object.fromEntries(checks.map(c => [c.name, c.status])));
  };

  useEffect(() => {
    checkAllServices();
    const interval = setInterval(checkAllServices, 5000);
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (status: ServiceStatus) => {
    switch (status) {
      case "online": return "text-green-400 border-green-500/30 bg-green-500/10";
      case "offline": return "text-red-400 border-red-500/30 bg-red-500/10";
      case "unknown": return "text-amber-400 border-amber-500/30 bg-amber-500/10";
    }
  };

  const getStatusIcon = (status: ServiceStatus) => {
    switch (status) {
      case "online": return "●";
      case "offline": return "●";
      case "unknown": return "●";
    }
  };

  return (
    <div className="mx-auto max-w-4xl px-4 py-12 sm:px-6">
      <div className="mb-8">
        <Link
          href="/"
          className="mb-4 inline-flex items-center gap-1 text-sm text-[var(--color-muted)] hover:text-[var(--color-accent)]"
        >
          ← Back to home
        </Link>
        <h1 className="display mb-2 text-3xl font-medium tracking-tight">Service Status</h1>
        <p className="text-lg text-[var(--color-muted)]">
          Real-time status of all monorepo services and APIs.
        </p>
      </div>

      <div className="space-y-4">
        {services.map((service) => {
          const status = statuses[service.name];
          return (
            <div
              key={service.name}
              className="flex items-center justify-between rounded-2xl border border-[var(--color-line)] bg-[var(--color-panel)] p-6"
            >
              <div className="flex items-center gap-4">
                <span className={`chip text-sm ${getStatusColor(status)}`}>
                  {getStatusIcon(status)} {status}
                </span>
                <div>
                  <h3 className="font-medium">{service.name}</h3>
                  <p className="text-sm text-[var(--color-muted)]">{service.description}</p>
                </div>
              </div>
              
              <div className="flex items-center gap-3">
                <span className="font-mono text-sm text-[var(--color-muted)]">:{service.port}</span>
                <Link
                  href={`${service.url}/docs`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-[var(--color-muted)] hover:text-[var(--color-accent)]"
                >
                  API Docs →
                </Link>
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-8 rounded-2xl border border-[var(--color-line)] bg-[var(--color-panel)] p-6">
        <h3 className="mb-3 font-medium">Quick Links</h3>
        <div className="grid gap-2 text-sm sm:grid-cols-2">
          <Link href="/" className="text-[var(--color-muted)] hover:text-[var(--color-accent)]">
            Portfolio Home
          </Link>
          <a href="/demos/llm-lab" className="text-[var(--color-muted)] hover:text-[var(--color-accent)]">
            LLM Lab Demo
          </a>
          <a href="/demos/agent-desk" className="text-[var(--color-muted)] hover:text-[var(--color-accent)]">
            Agent Desk Demo
          </a>
          <a href="/demos/research-digest" className="text-[var(--color-muted)] hover:text-[var(--color-accent)]">
            Research Digest Demo
          </a>
          <button
            type="button"
            onClick={checkAllServices}
            className="text-left text-[var(--color-muted)] hover:text-[var(--color-accent)]"
          >
            ↻ Refresh Status
          </button>
        </div>
      </div>

      <div className="mt-6 text-center text-xs text-[var(--color-muted)]">
        Status checks run every 5 seconds • Last updated: {new Date().toLocaleTimeString()}
      </div>
    </div>
  );
}