/**
 * API URLs for Research Digest.
 * SSE streams must hit the FastAPI backend directly — Next.js rewrites buffer
 * event-stream responses and EventSource never receives incremental events.
 */
const ZONE_BASE = (process.env.NEXT_PUBLIC_ZONE_BASE_PATH || "").replace(/\/$/, "");
const API_ORIGIN = (process.env.NEXT_PUBLIC_RESEARCH_DIGEST_API_URL || "").replace(/\/$/, "");

export function apiUrl(path: string): string {
  const clean = path.startsWith("/") ? path : `/${path}`;
  if (API_ORIGIN && clean.startsWith("/api/")) {
    return `${API_ORIGIN}${clean}`;
  }
  return `${ZONE_BASE}${clean}` || clean;
}

export type Citation = { id: string; url: string; title: string };

export type Paragraph = {
  text: string;
  citations: Citation[];
  meta?: {
    score?: number;
    topics?: string[];
    kind?: string;
    source?: string;
    date?: string;
    authors?: string;
  };
};

export type Section = {
  heading: string;
  paragraphs: Paragraph[];
};

export type Review = {
  kind: string;
  date: string;
  mode?: string;
  title: string;
  lede: string;
  focus_query?: string | null;
  focus_keywords?: string[];
  profile?: string;
  matched_topics?: string[];
  topics?: { id: string; label: string; weight: number }[];
  sections: Section[];
  stats?: {
    literature_items?: number;
    news_items?: number;
    fund_research_items?: number;
    claims_dropped?: number;
    sources_local?: boolean;
    sources?: Record<string, unknown>;
    items_ingested?: number;
    items_ranked?: number;
    focus_keywords?: string[];
  };
};

export type TopicsPayload = {
  profile?: string;
  focus?: string;
  topics: { id: string; label: string; weight: number; keywords?: string[] }[];
  sources?: {
    literature?: string[];
    news?: string[];
    fund_research?: string[];
  };
  free_only?: boolean;
};

export type DigestEvent = {
  type: string;
  timestamp?: string;
  run_id?: string;
  data?: Record<string, unknown>;
  message?: string;
};

export async function fetchLatest(): Promise<Review | null> {
  try {
    const res = await fetch(apiUrl("/api/latest"), { cache: "no-store" });
    if (!res.ok) return null;
    return (await res.json()) as Review;
  } catch {
    return null;
  }
}

export async function fetchTopics(): Promise<TopicsPayload | null> {
  try {
    const res = await fetch(apiUrl("/api/topics"), { cache: "no-store" });
    if (!res.ok) return null;
    return (await res.json()) as TopicsPayload;
  } catch {
    return null;
  }
}

export async function startRun(
  live = true,
  focusQuery = ""
): Promise<{ run_id: string; focus_query?: string | null }> {
  const res = await fetch(apiUrl("/api/run"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ live, focus_query: focusQuery.trim() }),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || `Failed to start run (${res.status})`);
  }
  return (await res.json()) as { run_id: string; focus_query?: string | null };
}

export async function fetchRun(runId: string): Promise<{
  status: string;
  review?: Review;
  error?: string;
}> {
  const res = await fetch(apiUrl(`/api/run/${runId}`), { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to load run ${runId}`);
  return res.json();
}
