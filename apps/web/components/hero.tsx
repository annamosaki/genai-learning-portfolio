"use client";

import Link from "next/link";
import { cv } from "@content/cv";
import { useApp } from "./providers";
import { t } from "@/lib/i18n";

export function Hero() {
  const { locale } = useApp();
  const d = t(locale);

  return (
    <section className="relative mx-auto max-w-6xl overflow-hidden px-4 pb-16 pt-14 sm:px-6 sm:pt-20">
      <div className="mesh-grid pointer-events-none absolute inset-0 -z-10 opacity-60" />
      <div className="chip mb-5">
        <span className="h-1.5 w-1.5 rounded-full bg-[var(--color-accent)]" />
        {d.hero.seeking}
      </div>
      <h1 className="display max-w-4xl text-5xl leading-[0.95] text-[var(--color-text)] sm:text-6xl md:text-7xl">
        {cv.name}
      </h1>
      <p className="mt-4 max-w-2xl text-lg text-[var(--color-accent-2)] sm:text-xl">{cv.title}</p>
      <p className="mt-6 max-w-2xl text-base leading-relaxed text-[var(--color-muted)] sm:text-lg">
        {cv.summary}
      </p>
      <div className="mt-8 flex flex-wrap gap-3">
        <Link href="/#projects" className="btn btn-primary">
          {d.hero.ctaWork}
        </Link>
        <a href={`mailto:${cv.email}`} className="btn btn-ghost">
          {d.hero.ctaContact}
        </a>
      </div>
      <div className="mt-10 flex flex-wrap gap-2">
        {cv.skills.ml.slice(0, 5).map((s) => (
          <span key={s} className="chip">
            {s}
          </span>
        ))}
        <span className="chip">{cv.location}</span>
      </div>
    </section>
  );
}
