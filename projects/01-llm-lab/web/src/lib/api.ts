/**
 * Absolute-from-origin API URL that respects Multi Zones basePath.
 * NEXT_PUBLIC_ZONE_BASE_PATH is set in next.config / start.sh
 * (e.g. /demos/llm-lab). Empty when running the demo standalone.
 */
const BASE = (process.env.NEXT_PUBLIC_ZONE_BASE_PATH || "").replace(/\/$/, "");

export function apiUrl(path: string): string {
  const clean = path.startsWith("/") ? path : `/${path}`;
  return `${BASE}${clean}` || clean;
}
