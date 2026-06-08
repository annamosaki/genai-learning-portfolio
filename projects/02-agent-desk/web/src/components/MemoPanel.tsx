'use client';

import { motion, AnimatePresence } from 'framer-motion';
import {
  ChevronDown,
  ChevronRight,
  Copy,
  Download,
  Eye,
  FileDown,
  FileText,
  List,
  Loader2,
  Maximize2,
  X,
} from 'lucide-react';
import { clsx } from 'clsx';
import { Fragment, ReactNode, useMemo, useState } from 'react';
import { exportMemoToPdf } from '@/lib/exportMemoPdf';

interface MemoPanelProps {
  memo?: string;
  isLoading: boolean;
  embedded?: boolean;
  ticker?: string;
}

interface MemoSection {
  id: string;
  title: string;
  level: number;
  lines: string[];
}

function slugify(text: string) {
  return stripMd(text)
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '');
}

/** Remove common markdown markers for plain display (TOC, meta). */
function stripMd(text: string): string {
  return text
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/\*([^*]+)\*/g, '$1')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/^#+\s*/, '')
    .trim();
}

function readingTime(text: string) {
  const words = text.trim().split(/\s+/).filter(Boolean).length;
  return Math.max(1, Math.ceil(words / 200));
}

/** Inline markdown: **bold**, *italic*, `code`, [links](url) */
function renderInline(text: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  // Split on bold, italic, code, links (order-safe-ish)
  const re =
    /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`|\[[^\]]+\]\([^)]+\))/g;
  const parts = text.split(re);

  parts.forEach((part, i) => {
    if (!part) return;
    if (part.startsWith('**') && part.endsWith('**') && part.length > 4) {
      nodes.push(
        <strong key={i} className="text-text font-semibold">
          {part.slice(2, -2)}
        </strong>
      );
    } else if (
      part.startsWith('*') &&
      part.endsWith('*') &&
      part.length > 2 &&
      !part.startsWith('**')
    ) {
      nodes.push(
        <em key={i} className="italic text-text/90">
          {part.slice(1, -1)}
        </em>
      );
    } else if (part.startsWith('`') && part.endsWith('`') && part.length > 2) {
      nodes.push(
        <code
          key={i}
          className="px-1 py-0.5 rounded bg-void/80 border border-line font-mono text-[11px] text-accent"
        >
          {part.slice(1, -1)}
        </code>
      );
    } else {
      const linkMatch = part.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
      if (linkMatch) {
        nodes.push(
          <a
            key={i}
            href={linkMatch[2]}
            target="_blank"
            rel="noopener noreferrer"
            className="text-accent underline underline-offset-2 hover:text-text"
          >
            {linkMatch[1]}
          </a>
        );
      } else {
        nodes.push(<Fragment key={i}>{part}</Fragment>);
      }
    }
  });

  return nodes;
}

function isHeadingLine(line: string): { level: number; title: string } | null {
  if (line.startsWith('### ')) return { level: 3, title: line.slice(4).trim() };
  if (line.startsWith('## ')) return { level: 2, title: line.slice(3).trim() };
  // Do NOT treat "1. **Something**" as headings — those are ordered list items.
  // Standalone bold title line (no colon) can still be a soft heading.
  if (/^\*\*[^*]+\*\*\s*$/.test(line) && !line.includes(':')) {
    return { level: 2, title: line.trim() };
  }
  return null;
}

function parseSections(memo: string): {
  title: string;
  sections: MemoSection[];
  meta: Record<string, string>;
  preamble: string[];
} {
  const lines = memo.split('\n');
  let title = 'Investment Memo';
  const meta: Record<string, string> = {};
  const sections: MemoSection[] = [];
  const preamble: string[] = [];
  let current: MemoSection | null = null;
  let sawTitle = false;

  for (const line of lines) {
    if (!sawTitle && line.startsWith('# ')) {
      title = line.slice(2).trim();
      sawTitle = true;
      continue;
    }

    // Meta lines: **Key**: value  or  **Key:** value
    const metaMatch = line.match(/^\*\*([^*]+)\*\*\s*:\s*(.+)$/);
    if (metaMatch && !current) {
      meta[metaMatch[1].trim().toLowerCase()] = metaMatch[2].trim();
      continue;
    }

    const heading = isHeadingLine(line);
    if (heading) {
      current = {
        id: slugify(heading.title) || `section-${sections.length}`,
        title: heading.title,
        level: heading.level,
        lines: [],
      };
      // Ensure unique ids
      if (sections.some((s) => s.id === current!.id)) {
        current.id = `${current.id}-${sections.length}`;
      }
      sections.push(current);
      continue;
    }

    if (current) current.lines.push(line);
    else if (line.trim()) preamble.push(line);
  }

  return { title, sections, meta, preamble };
}

function SectionBody({ lines }: { lines: string[] }) {
  const blocks: ReactNode[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    if (!line.trim()) {
      blocks.push(<div key={`sp-${i}`} className="h-2" />);
      i += 1;
      continue;
    }

    if (line.startsWith('---')) {
      blocks.push(<hr key={`hr-${i}`} className="border-line my-4" />);
      i += 1;
      continue;
    }

    if (line.startsWith('### ')) {
      blocks.push(
        <h4 key={`h-${i}`} className="text-sm font-semibold text-text mt-4 mb-1.5">
          {renderInline(line.slice(4))}
        </h4>
      );
      i += 1;
      continue;
    }

    if (line.startsWith('> ')) {
      const quote: string[] = [];
      while (i < lines.length && lines[i].startsWith('> ')) {
        quote.push(lines[i].slice(2));
        i += 1;
      }
      blocks.push(
        <blockquote
          key={`q-${i}`}
          className="border-l-2 border-accent/50 pl-3 my-2 text-sm text-muted italic"
        >
          {quote.map((q, qi) => (
            <p key={qi} className="mb-1 last:mb-0">
              {renderInline(q)}
            </p>
          ))}
        </blockquote>
      );
      continue;
    }

    // Unordered list
    if (/^[-*]\s+/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^[-*]\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^[-*]\s+/, ''));
        i += 1;
      }
      blocks.push(
        <ul key={`ul-${i}`} className="my-2 space-y-1.5 pl-1">
          {items.map((item, ii) => (
            <li
              key={ii}
              className="ml-4 list-disc marker:text-accent/70 text-sm text-muted leading-relaxed"
            >
              {renderInline(item)}
            </li>
          ))}
        </ul>
      );
      continue;
    }

    // Ordered list — keep consecutive items in ONE <ol> even across blank lines /
    // continuation paragraphs so numbering stays 1,2,3… (not a fresh 1. each time).
    if (/^\d+\.\s+/.test(line)) {
      type OlItem = { title: string; body: string[] };
      const items: OlItem[] = [];

      while (i < lines.length) {
        // skip blank lines between items
        while (i < lines.length && !lines[i].trim()) i += 1;
        if (i >= lines.length) break;
        if (!/^\d+\.\s+/.test(lines[i])) break;
        // stop if we hit a real markdown heading / hr / quote / bullet
        // (already checked it's numbered)

        const head = lines[i].replace(/^\d+\.\s+/, '');
        i += 1;
        const body: string[] = [];
        while (i < lines.length) {
          const nxt = lines[i];
          if (!nxt.trim()) {
            // peek ahead: blank then another "N." continues the list; blank then
            // heading/bullet ends item but list may continue after blanks.
            let j = i + 1;
            while (j < lines.length && !lines[j].trim()) j += 1;
            if (j < lines.length && /^\d+\.\s+/.test(lines[j])) {
              i = j; // jump to next numbered item
              break;
            }
            // blank then normal text = still part of this item
            if (
              j < lines.length &&
              !lines[j].startsWith('#') &&
              !lines[j].startsWith('---') &&
              !lines[j].startsWith('> ') &&
              !/^[-*]\s+/.test(lines[j]) &&
              !/^\d+\.\s+/.test(lines[j])
            ) {
              i += 1;
              continue;
            }
            // blank then end / other block
            break;
          }
          if (
            nxt.startsWith('#') ||
            nxt.startsWith('---') ||
            nxt.startsWith('> ') ||
            /^[-*]\s+/.test(nxt) ||
            /^\d+\.\s+/.test(nxt)
          ) {
            break;
          }
          body.push(nxt);
          i += 1;
        }
        items.push({ title: head, body });
      }

      blocks.push(
        <ol
          key={`ol-${i}`}
          className="my-3 space-y-3 list-none pl-0 counter-reset"
          style={{ counterReset: 'memo-ol' }}
        >
          {items.map((item, ii) => (
            <li
              key={ii}
              className="flex gap-3 text-sm text-muted leading-relaxed"
              style={{ counterIncrement: 'memo-ol' }}
            >
              <span
                className="shrink-0 w-6 h-6 rounded-md bg-accent/15 text-accent font-semibold text-xs flex items-center justify-center mt-0.5"
                aria-hidden
              >
                {ii + 1}
              </span>
              <div className="min-w-0 flex-1 space-y-1.5">
                <div>{renderInline(item.title)}</div>
                {item.body.map((b, bi) => (
                  <p key={bi} className="text-muted/90">
                    {renderInline(b)}
                  </p>
                ))}
              </div>
            </li>
          ))}
        </ol>
      );
      continue;
    }

    // Paragraph — merge consecutive non-empty plain lines
    const para: string[] = [line];
    i += 1;
    while (
      i < lines.length &&
      lines[i].trim() &&
      !lines[i].startsWith('#') &&
      !lines[i].startsWith('---') &&
      !lines[i].startsWith('> ') &&
      !/^[-*]\s+/.test(lines[i]) &&
      !/^\d+\.\s+/.test(lines[i])
    ) {
      para.push(lines[i]);
      i += 1;
    }
    blocks.push(
      <p key={`p-${i}`} className="text-sm text-muted leading-relaxed mb-2">
        {renderInline(para.join(' '))}
      </p>
    );
  }

  return <div className="space-y-0.5">{blocks}</div>;
}

function MemoReader({
  memo,
  ticker,
  onClose,
}: {
  memo: string;
  ticker?: string;
  onClose: () => void;
}) {
  const { title, sections, meta, preamble } = useMemo(() => parseSections(memo), [memo]);
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());
  const [showRaw, setShowRaw] = useState(false);
  const [activeSection, setActiveSection] = useState<string | null>(sections[0]?.id ?? null);
  const [pdfBusy, setPdfBusy] = useState(false);

  const toggleSection = (id: string) => {
    setCollapsed((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleDownload = () => {
    const blob = new Blob([memo], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${ticker || 'investment'}-memo.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handlePdf = async () => {
    setPdfBusy(true);
    try {
      await exportMemoToPdf(memo, { ticker, title: stripMd(title) });
    } catch (err) {
      console.error('PDF export failed', err);
    } finally {
      setPdfBusy(false);
    }
  };

  return (
    <motion.div
      className="fixed inset-0 z-50 bg-black/85 flex items-stretch p-3 md:p-5"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      onClick={onClose}
    >
      <motion.div
        className="flex-1 bg-surface border border-line rounded-lg overflow-hidden flex flex-col min-h-0 max-w-6xl mx-auto w-full"
        initial={{ scale: 0.97, y: 8 }}
        animate={{ scale: 1, y: 0 }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="shrink-0 px-4 py-3 border-b border-line flex flex-wrap items-center justify-between gap-3">
          <div className="min-w-0">
            <h2 className="display text-lg text-text truncate">{stripMd(title)}</h2>
            <p className="text-xs text-muted mt-0.5">
              {readingTime(memo)} min read · {memo.split(/\s+/).filter(Boolean).length.toLocaleString()}{' '}
              words
            </p>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <button type="button" className="btn text-xs" onClick={() => setShowRaw((v) => !v)}>
              {showRaw ? 'Rendered' : 'Raw MD'}
            </button>
            <button
              type="button"
              className="btn btn-primary text-xs gap-1.5"
              onClick={handlePdf}
              disabled={pdfBusy}
              title="Export PDF"
            >
              {pdfBusy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <FileDown className="w-3.5 h-3.5" />}
              PDF
            </button>
            <button type="button" className="btn text-xs" onClick={handleDownload} title="Download Markdown">
              <Download className="w-3.5 h-3.5" />
            </button>
            <button type="button" className="btn" onClick={onClose}>
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {Object.keys(meta).length > 0 && (
          <div className="shrink-0 px-4 py-3 border-b border-line grid grid-cols-2 md:grid-cols-4 gap-2">
            {Object.entries(meta)
              .slice(0, 4)
              .map(([k, v]) => (
                <div key={k} className="bg-panel border border-line rounded-lg p-2.5">
                  <div className="text-[10px] uppercase tracking-wide text-muted mb-0.5">{k}</div>
                  <div className="text-xs font-mono text-text truncate">{stripMd(v)}</div>
                </div>
              ))}
          </div>
        )}

        <div className="flex-1 flex min-h-0 overflow-hidden">
          {!showRaw && sections.length > 0 && (
            <aside className="hidden md:flex w-56 shrink-0 flex-col border-r border-line bg-panel/40 overflow-y-auto">
              <div className="px-3 py-2 text-[10px] uppercase tracking-wide text-muted border-b border-line">
                Contents
              </div>
              {sections.map((s) => (
                <button
                  key={s.id}
                  type="button"
                  onClick={() => {
                    setActiveSection(s.id);
                    document
                      .getElementById(`memo-${s.id}`)
                      ?.scrollIntoView({ behavior: 'smooth', block: 'start' });
                  }}
                  className={clsx(
                    'text-left px-3 py-2.5 text-xs border-b border-line/50 transition-colors',
                    activeSection === s.id
                      ? 'bg-accent/10 text-accent'
                      : 'text-muted hover:text-text hover:bg-panel'
                  )}
                >
                  <span className="line-clamp-2 leading-snug">{stripMd(s.title)}</span>
                </button>
              ))}
            </aside>
          )}

          <div className="flex-1 overflow-y-auto p-5 md:p-8">
            {showRaw ? (
              <pre className="text-[11px] font-mono text-muted whitespace-pre-wrap leading-relaxed bg-panel border border-line rounded-lg p-4">
                {memo}
              </pre>
            ) : sections.length > 0 ? (
              <div className="max-w-3xl mx-auto space-y-4">
                {preamble.length > 0 && (
                  <div className="mb-2">
                    <SectionBody lines={preamble} />
                  </div>
                )}
                {sections.map((section) => {
                  const isOpen = !collapsed.has(section.id);
                  return (
                    <section
                      key={section.id}
                      id={`memo-${section.id}`}
                      className="bg-panel/50 border border-line rounded-lg overflow-hidden"
                    >
                      <button
                        type="button"
                        onClick={() => toggleSection(section.id)}
                        className="w-full flex items-center gap-2 px-4 py-3 text-left hover:bg-panel transition-colors"
                      >
                        {isOpen ? (
                          <ChevronDown className="w-4 h-4 text-accent shrink-0" />
                        ) : (
                          <ChevronRight className="w-4 h-4 text-muted shrink-0" />
                        )}
                        <h3
                          className={clsx(
                            'font-semibold leading-snug',
                            section.level === 2 ? 'text-base text-text' : 'text-sm text-text'
                          )}
                        >
                          {renderInline(section.title)}
                        </h3>
                      </button>
                      <AnimatePresence initial={false}>
                        {isOpen && (
                          <motion.div
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: 'auto', opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            className="overflow-hidden"
                          >
                            <div className="px-4 pb-4 border-t border-line/60 pt-3">
                              <SectionBody lines={section.lines} />
                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </section>
                  );
                })}
              </div>
            ) : (
              <div className="max-w-3xl mx-auto">
                <SectionBody lines={memo.split('\n')} />
              </div>
            )}
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
}

export default function MemoPanel({ memo, isLoading, embedded = false, ticker }: MemoPanelProps) {
  const [readerOpen, setReaderOpen] = useState(false);
  const [pdfBusy, setPdfBusy] = useState(false);
  const parsed = useMemo(() => (memo ? parseSections(memo) : null), [memo]);

  const handleDownload = () => {
    if (!memo) return;
    const blob = new Blob([memo], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${ticker || 'investment'}-memo.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handlePdf = async () => {
    if (!memo) return;
    setPdfBusy(true);
    try {
      await exportMemoToPdf(memo, {
        ticker,
        title: parsed ? stripMd(parsed.title) : undefined,
      });
    } catch (err) {
      console.error('PDF export failed', err);
    } finally {
      setPdfBusy(false);
    }
  };

  const handleCopy = async () => {
    if (memo) await navigator.clipboard.writeText(memo);
  };

  const toolbar = memo && (
    <div className="shrink-0 flex items-center justify-between gap-2 px-4 py-2 border-b border-line bg-surface/60">
      <div className="flex items-center gap-2 text-[11px] text-muted min-w-0">
        <List className="w-3.5 h-3.5 shrink-0" />
        <span className="truncate">
          {parsed?.sections.length ?? 0} sections · {memo ? readingTime(memo) : 0} min read
        </span>
      </div>
      <div className="flex items-center gap-1 shrink-0">
        <button
          type="button"
          className="btn text-xs py-1.5 px-2.5 gap-1.5"
          onClick={() => setReaderOpen(true)}
          title="Reader mode"
        >
          <Maximize2 className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">Expand</span>
        </button>
        <button
          type="button"
          className="btn btn-primary text-xs py-1.5 px-2.5 gap-1.5"
          onClick={handlePdf}
          disabled={pdfBusy}
          title="Export PDF"
        >
          {pdfBusy ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <FileDown className="w-3.5 h-3.5" />
          )}
          <span className="hidden sm:inline">PDF</span>
        </button>
        <button type="button" className="btn text-xs p-1.5" onClick={handleCopy} title="Copy">
          <Copy className="w-3.5 h-3.5" />
        </button>
        <button type="button" className="btn text-xs p-1.5" onClick={handleDownload} title="Download Markdown">
          <Download className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );

  const content = (
    <div className={clsx('overflow-y-auto', embedded ? 'p-0' : 'flex-1 p-4')}>
      {isLoading ? (
        <div className="p-4 space-y-3">
          {[0.75, 0.5, 1, 0.65].map((w, i) => (
            <div
              key={i}
              className="animate-pulse bg-panel border border-line h-4 rounded-lg"
              style={{ width: `${w * 100}%` }}
            />
          ))}
          <div className="animate-pulse bg-panel border border-line h-28 rounded-lg" />
        </div>
      ) : memo && parsed ? (
        <div className="p-4 md:p-5 max-w-3xl">
          <h1 className="display text-xl text-accent mb-1">{stripMd(parsed.title)}</h1>
          {Object.keys(parsed.meta).length > 0 && (
            <div className="flex flex-wrap gap-2 mb-4 mt-2">
              {Object.entries(parsed.meta)
                .slice(0, 3)
                .map(([k, v]) => (
                  <span key={k} className="chip bg-panel text-text">
                    {k}: <span className="font-mono text-accent">{stripMd(v)}</span>
                  </span>
                ))}
            </div>
          )}
          {parsed.preamble.length > 0 && (
            <div className="mb-4">
              <SectionBody lines={parsed.preamble.slice(0, 8)} />
            </div>
          )}
          {parsed.sections.length > 0 ? (
            <div className="space-y-3">
              {parsed.sections.slice(0, 4).map((section) => (
                <div key={section.id} className="bg-panel border border-line rounded-lg p-3">
                  <h3 className="text-sm font-semibold text-text mb-2">
                    {renderInline(section.title)}
                  </h3>
                  <div className="line-clamp-5">
                    <SectionBody lines={section.lines.slice(0, 8)} />
                  </div>
                </div>
              ))}
              {parsed.sections.length > 4 && (
                <button
                  type="button"
                  className="btn w-full text-sm"
                  onClick={() => setReaderOpen(true)}
                >
                  <Eye className="w-4 h-4 mr-2" />
                  View full memo ({parsed.sections.length} sections)
                </button>
              )}
            </div>
          ) : (
            <div className="text-sm text-muted leading-relaxed">
              <SectionBody lines={memo.split('\n').slice(0, 24)} />
              {memo.split('\n').length > 24 && (
                <button
                  type="button"
                  className="btn mt-4 text-sm"
                  onClick={() => setReaderOpen(true)}
                >
                  Read full memo
                </button>
              )}
            </div>
          )}
        </div>
      ) : (
        <div className="h-full flex flex-col items-center justify-center text-muted py-12 px-4">
          <FileText className="w-10 h-10 mb-3 opacity-40" />
          <p className="text-sm text-center">Investment memo will appear here when the run completes.</p>
          <p className="text-xs mt-1 opacity-70 text-center">
            Approve the plan gate, then wait for the scribe agent.
          </p>
        </div>
      )}
    </div>
  );

  const reader = readerOpen && memo && (
    <MemoReader memo={memo} ticker={ticker} onClose={() => setReaderOpen(false)} />
  );

  if (embedded) {
    return (
      <div className="flex flex-col">
        {toolbar}
        {content}
        {reader}
      </div>
    );
  }

  return (
    <div className="bg-surface border border-line rounded-lg h-96 flex flex-col overflow-hidden">
      <div className="px-4 py-3 border-b border-line">
        <h3 className="text-[10px] uppercase tracking-wide text-muted">Investment Memo</h3>
      </div>
      {toolbar}
      {content}
      {reader}
    </div>
  );
}
