"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { cv } from "@content/cv";
import { isZoneHref } from "./zone-link";

const links = [
  { label: "Home", href: "/" },
  { label: "Projects", href: "/#projects" },
  { label: "Experience", href: "/#experience" },
  { label: "Wins", href: "/#wins" },
  { label: "Ask Anna", href: "/ask" },
  { label: "Status", href: "/status" },
  { label: "LLM Lab Demo", href: "/demos/llm-lab" },
  { label: "Agent Desk Demo", href: "/demos/agent-desk" },
  { label: "Download CV", href: "/api/cv" },
  ...cv.projects.map((p) => ({
    label: `${p.number} ${p.title}`,
    href: `/projects/${p.slug}`,
  })),
];

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const router = useRouter();

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((v) => !v);
      }
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    if (!needle) return links;
    return links.filter((l) => l.label.toLowerCase().includes(needle));
  }, [q]);

  if (!open) {
    return (
      <div className="pointer-events-none fixed bottom-4 right-4 z-50 hidden md:block">
        <span className="chip">⌘K</span>
      </div>
    );
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-black/70 px-4 pt-[15vh]"
      onClick={() => setOpen(false)}
      role="dialog"
      aria-modal="true"
      aria-label="Command palette"
    >
      <div
        className="w-full max-w-lg overflow-hidden rounded-2xl border border-[var(--color-line-strong)] bg-[var(--color-panel)] shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <input
          autoFocus
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Jump to…"
          className="w-full border-b border-[var(--color-line)] bg-transparent px-4 py-3 font-mono text-sm outline-none"
        />
        <ul className="max-h-72 overflow-auto py-2">
          {filtered.map((item) => (
            <li key={item.label + item.href}>
              <button
                type="button"
                className="flex w-full px-4 py-2 text-left text-sm hover:bg-[var(--color-panel-2)]"
                onClick={() => {
                  setOpen(false);
                  setQ("");
                  // Cross-zone demos need a hard navigation (plain location assign).
                  if (item.href.startsWith("/api") || isZoneHref(item.href)) {
                    window.location.href = item.href;
                  } else {
                    router.push(item.href);
                  }
                }}
              >
                {item.label}
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
