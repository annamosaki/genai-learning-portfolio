"use client";

import { cv } from "@content/cv";
import { useApp } from "./providers";
import { t } from "@/lib/i18n";

export function About() {
  const { locale } = useApp();
  const d = t(locale);

  return (
    <section id="experience" className="mx-auto max-w-6xl scroll-mt-24 px-4 py-16 sm:px-6">
      <div className="grid gap-10 lg:grid-cols-[1.15fr_0.85fr]">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.18em] text-[var(--color-accent)]">
            CV
          </p>
          <h2 className="display mt-2 text-4xl sm:text-5xl">{d.about.title}</h2>
          <div className="mt-8 space-y-6">
            {cv.experience.map((e) => (
              <article
                key={e.company + e.start}
                className="rounded-2xl border border-[var(--color-line)] bg-[var(--color-panel)] p-5"
              >
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <h3 className="display text-xl">{e.company}</h3>
                  <p className="font-mono text-xs text-[var(--color-muted)]">
                    {e.start} – {e.end}
                  </p>
                </div>
                <p className="mt-1 text-sm text-[var(--color-accent-2)]">{e.role}</p>
                <p className="mt-1 font-mono text-xs text-[var(--color-muted)]">{e.location}</p>
                <ul className="mt-3 space-y-2 text-sm text-[var(--color-muted)]">
                  {e.bullets.map((b) => (
                    <li key={b} className="flex gap-2">
                      <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-[var(--color-accent)]" />
                      <span>{b}</span>
                    </li>
                  ))}
                </ul>
              </article>
            ))}
          </div>

          {cv.priorProjects.length > 0 && (
            <div className="mt-10">
              <h3 className="display text-2xl">Selected academic projects</h3>
              <ul className="mt-4 space-y-3 text-sm text-[var(--color-muted)]">
                {cv.priorProjects.map((p) => (
                  <li
                    key={p}
                    className="rounded-xl border border-[var(--color-line)] bg-[var(--color-panel)] px-4 py-3"
                  >
                    {p}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        <aside className="space-y-4">
          <div className="glass rounded-2xl p-5">
            <h3 className="display text-2xl">{d.about.education}</h3>
            <ul className="mt-4 space-y-4">
              {cv.education.map((ed) => (
                <li key={ed.school}>
                  <p className="font-medium text-[var(--color-text)]">{ed.school}</p>
                  <p className="text-sm text-[var(--color-muted)]">{ed.degree}</p>
                  <p className="font-mono text-xs text-[var(--color-accent)]">{ed.years}</p>
                  {ed.notes?.map((n) => (
                    <p key={n} className="mt-1 text-xs text-[var(--color-muted)]">
                      {n}
                    </p>
                  ))}
                </li>
              ))}
            </ul>
          </div>

          <div className="glass rounded-2xl p-5">
            <h3 className="display text-2xl">{d.about.languages}</h3>
            <ul className="mt-4 space-y-2">
              {cv.languages.map((l) => (
                <li key={l.code} className="flex justify-between text-sm">
                  <span>{l.label}</span>
                  <span className="font-mono text-xs text-[var(--color-muted)]">{l.level}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="glass rounded-2xl p-5">
            <h3 className="display text-2xl">{d.about.stack}</h3>
            <p className="mt-3 font-mono text-xs leading-relaxed text-[var(--color-muted)]">
              {[...cv.skills.languages, ...cv.skills.ml, ...cv.skills.tools].join(" · ")}
            </p>
          </div>
        </aside>
      </div>
    </section>
  );
}
