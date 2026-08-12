"use client";

import Link from "next/link";
import { useApp } from "./providers";
import { t } from "@/lib/i18n";
import { ZoneLink } from "./zone-link";

function SunIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle cx="12" cy="12" r="4" stroke="currentColor" strokeWidth="1.75" />
      <path
        d="M12 2.5v2.25M12 19.25V21.5M4.04 4.04l1.59 1.59M18.37 18.37l1.59 1.59M2.5 12h2.25M19.25 12H21.5M4.04 19.96l1.59-1.59M18.37 5.63l1.59-1.59"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
      />
    </svg>
  );
}

function MoonIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M20.5 14.2A8.2 8.2 0 0 1 9.8 3.5 7.1 7.1 0 1 0 20.5 14.2Z"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function SiteHeader() {
  const { locale, setLocale, theme, toggleTheme } = useApp();
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
              <ZoneLink href="/demos/research-digest" className="block px-3 py-2 text-sm hover:bg-[var(--color-panel-2)] rounded">
                Research Digest
              </ZoneLink>
            </div>
          </div>
        </nav>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={toggleTheme}
            className="chip hover:border-[var(--color-accent)] hover:text-[var(--color-accent)]"
            aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
            title={theme === "dark" ? "Light mode" : "Dark mode"}
          >
            {theme === "dark" ? <SunIcon /> : <MoonIcon />}
          </button>
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
