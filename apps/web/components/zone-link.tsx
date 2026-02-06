import { type AnchorHTMLAttributes, type ReactNode } from "react";

/** Paths served by a child Multi Zone app (not the portfolio Next.js router). */
const ZONE_PREFIXES = ["/demos/llm-lab", "/demos/agent-desk"] as const;

export function isZoneHref(href: string): boolean {
  if (!href.startsWith("/")) return false;
  return ZONE_PREFIXES.some(
    (prefix) => href === prefix || href.startsWith(`${prefix}/`)
  );
}

type ZoneLinkProps = AnchorHTMLAttributes<HTMLAnchorElement> & {
  href: string;
  children: ReactNode;
};

/**
 * Cross-zone navigation must use a plain <a> so the browser does a hard load.
 * Soft navigation via next/link / router.push breaks with webpack "reading 'call'".
 */
export function ZoneLink({ href, children, ...rest }: ZoneLinkProps) {
  return (
    <a href={href} {...rest}>
      {children}
    </a>
  );
}
