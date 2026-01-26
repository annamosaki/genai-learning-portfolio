"use client";

import Link from "next/link";
import { cv } from "@content/cv";
import { useApp } from "./providers";
import { t } from "@/lib/i18n";
import { ZoneLink } from "./zone-link";

export function ProjectGrid() {
  const { locale } = useApp();
  const d = t(locale);

  return (
    <section id="projects" className="mx-auto max-w-6xl scroll-mt-24 px-4 py-16 sm:px-6">
      <div className="mb-8 max-w-2xl">
        <p className="font-mono text-xs uppercase tracking-[0.18em] text-[var(--color-accent)]">
          Builds
        </p>
        <h2 className="display mt-2 text-4xl sm:text-5xl">{d.projects.title}</h2>
        <p className="mt-3 text-[var(--color-muted)]">{d.projects.subtitle}</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {cv.projects.map((p) => (
          <article
            key={p.slug}
            className="group relative overflow-hidden rounded-2xl border border-[var(--color-line)] bg-[var(--color-panel)] p-5 transition hover:border-[var(--color-accent)]/50 sm:p-6"
          >
            <div className="pointer-events-none absolute -right-8 -top-8 h-28 w-28 rounded-full bg-[var(--color-accent)]/10 blur-2xl transition group-hover:bg-[var(--color-accent)]/20" />
            <div className="flex items-start justify-between gap-3">
              <span className="font-mono text-xs text-[var(--color-muted)]">{p.number}</span>
              <span
                className={
                  p.status === "live"
                    ? "chip border-[var(--color-accent)]/40 text-[var(--color-accent)]"
                    : "chip text-[var(--color-accent)] border-[var(--color-accent)]/30"
                }
              >
                {p.status === "live" ? d.projects.live : d.projects.planned}
              </span>
            </div>
            <h3 className="display mt-4 text-2xl sm:text-3xl">
              <Link href={`/projects/${p.slug}`} className="hover:text-[var(--color-accent)]">
                {p.title}
              </Link>
            </h3>
            <p className="mt-2 text-sm leading-relaxed text-[var(--color-muted)]">{p.tagline}</p>

            <div className="mt-5 flex flex-wrap gap-1.5">
              {p.stack.map((s) => (
                <span key={s} className="chip">
                  {s}
                </span>
              ))}
            </div>

            {p.status === "live" && (p.demoUrl || p.repoUrl) ? (
              <div className="mt-5 flex flex-wrap gap-2 border-t border-[var(--color-line)] pt-4">
                {p.demoUrl && (
                  <ZoneLink href={p.demoUrl} className="btn btn-primary text-xs">
                    {d.projects.openDemo}
                  </ZoneLink>
                )}
                {p.repoUrl && (
                  <a
                    href={p.repoUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="btn text-xs"
                  >
                    {d.projects.source}
                  </a>
                )}
              </div>
            ) : (
              <div className="mt-5 border-t border-[var(--color-line)] pt-4">
                <p className="font-mono text-[10px] uppercase tracking-wider text-[var(--color-accent-2)]">
                  What will be here
                </p>
                <ul className="mt-2 space-y-1.5 text-sm text-[var(--color-muted)]">
                  {p.comingSoon.map((item) => (
                    <li key={item} className="flex gap-2">
                      <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-[var(--color-accent)]" />
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </article>
        ))}
      </div>
    </section>
  );
}
