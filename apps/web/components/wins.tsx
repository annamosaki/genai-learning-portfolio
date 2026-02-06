"use client";

import { cv } from "@content/cv";
import { useApp } from "./providers";
import { t } from "@/lib/i18n";

export function Wins() {
  const { locale } = useApp();
  const d = t(locale);

  return (
    <section id="wins" className="mx-auto max-w-6xl scroll-mt-24 px-4 py-16 sm:px-6">
      <h2 className="display text-4xl sm:text-5xl">{d.wins.title}</h2>
      <div className="mt-8 grid gap-4 md:grid-cols-3">
        {cv.wins.map((w) => (
          <article
            key={w.title + w.org}
            className="rounded-2xl border border-[var(--color-accent)]/25 bg-gradient-to-br from-[var(--color-accent)]/10 to-transparent p-5"
          >
            <p className="font-mono text-xs uppercase tracking-wider text-[var(--color-accent)]">
              Award
            </p>
            <h3 className="display mt-2 text-2xl">{w.title}</h3>
            <p className="mt-2 text-sm font-medium text-[var(--color-text)]">{w.org}</p>
            <p className="mt-2 text-sm text-[var(--color-muted)]">{w.detail}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
