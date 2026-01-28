"use client";

import Link from "next/link";
import { useApp } from "./providers";
import { t } from "@/lib/i18n";
import { ZoneLink } from "./zone-link";

export function SiteHeader() {
  const { locale, setLocale } = useApp();
  const d = t(locale);

  return (
    <header className="sticky top-0 z-40 border-b border-[var(--color-line)] bg-[color-mix(in_oklab,var(--color-void)_78%,transparent)] backdrop-blur-xl">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-3 sm:px-6">
        <Link href="/" className="display text-lg tracking-tight text-[var(--color-text)]" title="Back to home">
          Anna<span className="text-[var(--color-accent)]">.</span>Mosaki
        </Link>
        <nav className="hidden items-center gap-6 text-sm text-[var(--color-muted)] md:flex">
          <Link className="hover:text-[var(--color-accent)]" href="/#projects">
            {d.nav.work}
          </Link>
          <Link className="hover:text-[var(--color-accent)]" href="/#experience">
            {d.nav.about}
          </Link>
          <Link className="hover:text-[var(--color-accent)]" href="/#wins">
            {d.nav.wins}
          </Link>
          <Link className="hover:text-[var(--color-accent)]" href="/ask">
            {d.nav.ask}
          </Link>
          <div className="relative group">
            <button className="hover:text-[var(--color-accent)]">
              {d.nav.demos}
            </button>
            <div className="absolute top-full left-0 mt-1 hidden group-hover:block w-48 rounded-lg border border-[var(--color-line)] bg-[var(--color-panel)] p-2 shadow-xl">
              <ZoneLink href="/demos/llm-lab" className="block px-3 py-2 text-sm hover:bg-[var(--color-panel-2)] rounded">
                LLM Lab
              </ZoneLink>
              <ZoneLink href="/demos/agent-desk" className="block px-3 py-2 text-sm hover:bg-[var(--color-panel-2)] rounded">
                Agent Desk
              </ZoneLink>
            </div>
          </div>
          <Link className="hover:text-[var(--color-accent)]" href="/status">
            {d.nav.status}
          </Link>
        </nav>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setLocale(locale === "en" ? "fr" : "en")}
            className="chip hover:border-[var(--color-accent)] hover:text-[var(--color-accent)]"
            aria-label="Toggle language"
          >
            {locale.toUpperCase()}
          </button>
          <Link href="/api/cv" className="btn btn-primary hidden text-sm sm:inline-flex">
            {d.nav.cv}
          </Link>
        </div>
      </div>
    </header>
  );
}
