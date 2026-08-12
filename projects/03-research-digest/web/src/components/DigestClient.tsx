"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { BookOpen, Building2, Newspaper, RefreshCw } from "lucide-react";
import { BackToPortfolio } from "@/components/BackToPortfolio";
import {
  apiUrl,
  fetchLatest,
  fetchRun,
  fetchTopics,
  startRun,
  type DigestEvent,
  type Paragraph,
  type Review,
  type Section,
  type TopicsPayload,
} from "@/lib/api";

const FOCUS_STORAGE_KEY = "research-digest:focus-query";

const SECTION_META: Record<
  string,
  { label: string; icon: typeof BookOpen; blurb: string }
> = {
  Literature: {
    label: "Papers",
    icon: BookOpen,
    blurb: "ArXiv + local seed — steered by your focus keywords",
  },
  News: {
    label: "News",
    icon: Newspaper,
    blurb: "Market notes (Finnhub free tier when keyed) + local digest",
  },
  "Fund research": {
    label: "Fund research",
    icon: Building2,
    blurb: "Jane Street, Two Sigma, Quantpedia, Robot Wealth, Newfound, Alpha Architect",
  },
};

function formatEvent(ev: DigestEvent): string {
  const d = ev.data || {};
  switch (ev.type) {
    case "run.started":
      if (d.focus) return `Starting with focus · ${String(d.focus).slice(0, 80)}`;
      return d.live === false ? "Starting offline review…" : "Starting live fetch…";
    case "source.fetching":
      if (d.feed) return `Fetching RSS · ${d.feed}`;
      if (d.query) return `Querying ArXiv…`;
      if (d.source === "finnhub") return "Fetching Finnhub news…";
      return `Fetching ${d.source || "source"}…`;
    case "source.fetched":
      if (d.feed) return `${d.feed}: ${d.count ?? 0} items`;
      return `${d.source || "source"}: ${d.count ?? 0} items`;
    case "source.skipped":
      return `Skipped ${d.feed || d.source || "source"}${d.reason ? ` — ${String(d.reason).slice(0, 80)}` : ""}`;
    case "rank.done":
      return `Ranked ${d.ranked ?? 0} items · topics: ${Array.isArray(d.topics) ? (d.topics as string[]).join(", ") : "—"}`;
    case "synthesize.done":
      return `Sections: ${Array.isArray(d.sections) ? (d.sections as string[]).join(" · ") : "—"}`;
    case "run.finished":
      return d.ok === false ? "Run finished with errors" : "Digest ready";
    case "error":
      return `Error: ${d.message || ev.message || "unknown"}`;
    case "keepalive":
      return "";
    default:
      return ev.type;
  }
}

function ItemCard({ p }: { p: Paragraph }) {
  const cite = p.citations?.[0];
  const topics = p.meta?.topics || [];
  return (
    <article className="group border-b border-line py-4 last:border-0">
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        {cite?.url ? (
          <a
            href={cite.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-[15px] font-medium text-text hover:text-accent transition-colors"
          >
            {cite.title || p.text.split(" — ")[0]}
          </a>
        ) : (
          <span className="text-[15px] font-medium">{p.text.split(" — ")[0]}</span>
        )}
        {typeof p.meta?.score === "number" && (
          <span className="font-mono text-[11px] text-muted">score {p.meta.score}</span>
        )}
      </div>
      <p className="mt-1.5 text-sm leading-relaxed text-muted">
        {p.text.includes(" — ") ? p.text.slice(p.text.indexOf(" — ") + 3) : null}
      </p>
      <div className="mt-2 flex flex-wrap gap-1.5">
        {p.meta?.source && <span className="chip">{p.meta.source}</span>}
        {p.meta?.date && <span className="chip">{p.meta.date}</span>}
        {topics.map((t) => (
          <span key={t} className="chip chip-accent">
            {t}
          </span>
        ))}
      </div>
    </article>
  );
}

function SectionBlock({ section }: { section: Section }) {
  if (section.heading === "Watchlist") {
    return (
      <div className="rounded-xl border border-line bg-panel/60 px-4 py-3 text-sm text-muted">
        {section.paragraphs[0]?.text}
      </div>
    );
  }
  const meta = SECTION_META[section.heading];
  const Icon = meta?.icon || BookOpen;
  return (
    <section className="min-w-0">
      <header className="mb-3 flex items-end justify-between gap-3 border-b border-line pb-3">
        <div>
          <div className="flex items-center gap-2">
            <Icon className="h-4 w-4 text-accent" aria-hidden />
            <h2 className="display text-xl text-text">{meta?.label || section.heading}</h2>
          </div>
          {meta?.blurb && <p className="mt-1 text-xs text-muted">{meta.blurb}</p>}
        </div>
        <span className="font-mono text-[11px] text-muted">{section.paragraphs.length}</span>
      </header>
      <div>
        {section.paragraphs.length === 0 ? (
          <p className="py-6 text-sm text-muted">No items matched this section.</p>
        ) : (
          section.paragraphs.map((p, i) => <ItemCard key={i} p={p} />)
        )}
      </div>
    </section>
  );
}

export function DigestClient() {
  const [review, setReview] = useState<Review | null>(null);
  const [topics, setTopics] = useState<TopicsPayload | null>(null);
  const [focusQuery, setFocusQuery] = useState("");
  const [running, setRunning] = useState(false);
  const [events, setEvents] = useState<DigestEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    try {
      const saved = localStorage.getItem(FOCUS_STORAGE_KEY);
      if (saved) setFocusQuery(saved);
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [r, t] = await Promise.all([fetchLatest(), fetchTopics()]);
        if (cancelled) return;
        setReview(r);
        setTopics(t);
        if (!r && !t) {
          setError("Could not reach Digest API — is it running on :8300?");
        }
        // Prefill focus from last successful run if localStorage empty.
        if (r?.focus_query) {
          setFocusQuery((prev) => prev || r.focus_query || "");
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : String(e));
        }
      }
    })();
    return () => {
      cancelled = true;
      esRef.current?.close();
    };
  }, []);

  const primarySections = useMemo(() => {
    const order = ["Literature", "News", "Fund research"];
    const map = new Map((review?.sections || []).map((s) => [s.heading, s]));
    return order.map(
      (h) => map.get(h) || ({ heading: h, paragraphs: [] as Paragraph[] })
    );
  }, [review]);

  const watch = review?.sections?.find((s) => s.heading === "Watchlist");

  const onFocusChange = useCallback((value: string) => {
    setFocusQuery(value);
    try {
      localStorage.setItem(FOCUS_STORAGE_KEY, value);
    } catch {
      /* ignore */
    }
  }, []);

  const regenerate = useCallback(async () => {
    setError(null);
    setRunning(true);
    setEvents([]);
    esRef.current?.close();

    try {
      const { run_id } = await startRun(true, focusQuery);
      const es = new EventSource(apiUrl(`/api/run/${run_id}/stream`));
      esRef.current = es;

      es.onmessage = async (msg) => {
        try {
          const parsed = JSON.parse(msg.data) as DigestEvent;
          if (parsed.type === "keepalive") return;
          setEvents((prev) => [...prev, parsed]);

          if (parsed.type === "run.finished" || parsed.type === "error") {
            es.close();
            esRef.current = null;
            const run = await fetchRun(run_id);
            if (run.review) setReview(run.review);
            else {
              const latest = await fetchLatest();
              if (latest) setReview(latest);
            }
            if (run.error) setError(run.error);
            setRunning(false);
          }
        } catch {
          /* ignore malformed */
        }
      };

      es.onerror = () => {
        es.close();
        esRef.current = null;
        setRunning(false);
        setError("SSE connection lost — try regenerate again.");
      };
    } catch (e) {
      setRunning(false);
      setError(e instanceof Error ? e.message : String(e));
    }
  }, [focusQuery]);

  const eventLines = events.map(formatEvent).filter(Boolean);
  const activeFocus = review?.focus_query || focusQuery.trim() || null;

  return (
    <div className="digest-shell">
      <div className="digest-glow" aria-hidden />
      <header className="relative z-10 flex flex-wrap items-center justify-between gap-4 border-b border-line px-5 py-4 md:px-8">
        <div className="flex items-center gap-4">
          <BackToPortfolio />
          <div className="h-4 w-px bg-line" />
          <div>
            <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted">
              Project 03
            </p>
            <h1 className="display text-2xl leading-none text-text md:text-3xl">
              Research Digest
            </h1>
          </div>
        </div>
        <button
          type="button"
          className="btn btn-primary gap-2"
          onClick={regenerate}
          disabled={running}
        >
          <RefreshCw className={`h-3.5 w-3.5 ${running ? "animate-spin" : ""}`} />
          {running ? "Fetching…" : "Regenerate"}
        </button>
      </header>

      <main className="relative z-10 mx-auto grid max-w-6xl gap-8 px-5 py-8 md:px-8 lg:grid-cols-[1fr_280px]">
        <div className="min-w-0 space-y-8">
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35 }}
          >
            <p className="max-w-2xl text-base leading-relaxed text-muted">
              {review?.lede ||
                topics?.focus ||
                "Time series applied to finance — and what quant desks are publishing next."}
            </p>
            <div className="mt-3 flex flex-wrap gap-3 font-mono text-[11px] text-muted">
              {review?.date && <span>Last run · {review.date}</span>}
              {review?.mode && <span className="text-accent">mode · {review.mode}</span>}
              {typeof review?.stats?.items_ranked === "number" && (
                <span>ranked · {review.stats.items_ranked}</span>
              )}
              {review?.stats?.sources_local === false && <span>live sources</span>}
            </div>
          </motion.div>

          <div className="rounded-xl border border-line bg-panel/70 p-4">
            <label htmlFor="focus-query" className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted">
              Focus field / keywords
            </label>
            <textarea
              id="focus-query"
              className="focus-field mt-2"
              value={focusQuery}
              onChange={(e) => onFocusChange(e.target.value)}
              placeholder='e.g. realized volatility, GARCH, TimesFM — or “market microstructure liquidity”'
              rows={3}
              maxLength={400}
              disabled={running}
            />
            <p className="mt-2 text-xs text-muted">
              Steers ArXiv queries and ranking for this run. Comma-separate terms, or write a short domain phrase.
            </p>
            {(review?.focus_keywords?.length || 0) > 0 && (
              <div className="mt-3 flex flex-wrap gap-1.5">
                {review!.focus_keywords!.map((kw) => (
                  <span key={kw} className="chip chip-accent">
                    {kw}
                  </span>
                ))}
              </div>
            )}
          </div>

          {error && (
            <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-sm text-amber-100">
              {error}
            </div>
          )}

          <div className="flex flex-wrap gap-1.5">
            {(topics?.topics || review?.topics || []).map((t) => (
              <span key={t.id} className="chip" title={`weight ${t.weight}`}>
                {t.label}
              </span>
            ))}
            {activeFocus && (
              <span className="chip chip-accent" title={activeFocus}>
                focus
              </span>
            )}
          </div>

          {watch && <SectionBlock section={watch} />}

          <div className="grid gap-10">
            <AnimatePresence mode="popLayout">
              {primarySections.map((section) => (
                <motion.div
                  key={section.heading}
                  layout
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3 }}
                >
                  <SectionBlock section={section} />
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        </div>

        <aside className="space-y-4 lg:sticky lg:top-6 lg:self-start">
          <div className="rounded-xl border border-line bg-panel/80 p-4">
            <h3 className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted">
              Run progress
            </h3>
            <ul className="mt-3 max-h-72 space-y-2 overflow-y-auto font-mono text-[11px] leading-snug text-muted">
              {eventLines.length === 0 && !running && (
                <li>Idle — set a focus, then Regenerate.</li>
              )}
              {eventLines.map((line, i) => (
                <li key={`${i}-${line.slice(0, 24)}`} className="border-l border-accent/40 pl-2">
                  {line}
                </li>
              ))}
              {running && eventLines.length === 0 && <li className="text-accent">Connecting…</li>}
            </ul>
          </div>
          <div className="rounded-xl border border-line bg-panel/50 p-4 text-xs text-muted">
            <p className="font-mono text-[10px] uppercase tracking-[0.16em]">Sources</p>
            <ul className="mt-2 space-y-1">
              <li>ArXiv API (free)</li>
              <li>Curated fund/quant RSS</li>
              <li>Finnhub free tier (optional key)</li>
              <li>Local JSONL seed / fallback</li>
            </ul>
          </div>
        </aside>
      </main>
    </div>
  );
}
