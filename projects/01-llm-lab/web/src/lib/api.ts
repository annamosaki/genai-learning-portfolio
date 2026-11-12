/**
 * API calls go straight to the lab API host.
 * Proxying /demos/llm-lab/api/* through the portfolio CloudFront
 * distribution returns 403, because that distribution cannot call the lab one.
 */
const ZONE_BASE = (process.env.NEXT_PUBLIC_ZONE_BASE_PATH || "").replace(/\/$/, "");
const API_ORIGIN = (process.env.NEXT_PUBLIC_LAB_API_URL || "").replace(/\/$/, "");

export function apiUrl(path: string): string {
  const clean = path.startsWith("/") ? path : `/${path}`;
  if (API_ORIGIN && clean.startsWith("/api/")) {
    return `${API_ORIGIN}${clean}`;
  }
  return `${ZONE_BASE}${clean}` || clean;
}
