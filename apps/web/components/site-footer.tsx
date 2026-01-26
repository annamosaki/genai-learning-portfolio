"use client";

import { cv } from "@content/cv";
import { useApp } from "./providers";
import { t } from "@/lib/i18n";

export function SiteFooter() {
  const { locale } = useApp();
  const d = t(locale);
  return (
    <footer className="mt-20 border-t border-[var(--color-line)]">
      <div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-10 text-sm text-[var(--color-muted)] sm:flex-row sm:items-center sm:justify-between sm:px-6">
        <p className="display text-[var(--color-text)]">{d.footer.built}</p>
        <div className="flex flex-wrap gap-4 font-mono text-xs">
          <a className="hover:text-[var(--color-accent)]" href={`mailto:${cv.email}`}>
            {cv.email}
          </a>
          <a className="hover:text-[var(--color-accent)]" href={cv.links.github} target="_blank" rel="noreferrer">
            GitHub
          </a>
          <a className="hover:text-[var(--color-accent)]" href={cv.links.linkedin} target="_blank" rel="noreferrer">
            LinkedIn
          </a>
          <span>{cv.location}</span>
        </div>
      </div>
    </footer>
  );
}
