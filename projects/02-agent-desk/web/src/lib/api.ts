/**
 * API URLs for Agent Desk.
 * SSE streams must hit the FastAPI backend directly — Next.js rewrites buffer
 * event-stream responses and EventSource never receives incremental events.
 */
const ZONE_BASE = (process.env.NEXT_PUBLIC_ZONE_BASE_PATH || "").replace(/\/$/, "");
const API_ORIGIN = (process.env.NEXT_PUBLIC_AGENT_DESK_API_URL || "").replace(/\/$/, "");

export function apiUrl(path: string): string {
  const clean = path.startsWith("/") ? path : `/${path}`;
  if (API_ORIGIN && clean.startsWith("/api/")) {
    return `${API_ORIGIN}${clean}`;
  }
  return `${ZONE_BASE}${clean}` || clean;
}
