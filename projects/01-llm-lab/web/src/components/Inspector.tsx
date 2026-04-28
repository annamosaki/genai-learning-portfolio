'use client';

import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { clsx } from 'clsx';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Activity,
  Bot,
  ChevronDown,
  ChevronRight,
  Clock,
  Code2,
  Database,
  DollarSign,
  FileStack,
  FileText,
  ListOrdered,
  Network,
  Shield,
} from 'lucide-react';
import type { ChatResponse, TraceData } from '@/lib/types';
import { CORPUS_LEVELS } from '@/lib/constants';
import { GraphCanvas } from './GraphCanvas';
import { CorpusBrowser } from './CorpusBrowser';

interface InspectorProps {
  lastResponse: ChatResponse | null;
  selectedLevel: string;
}

type TabKey =
  | 'overview'
  | 'timeline'
  | 'chunks'
  | 'prompt'
  | 'messages'
  | 'graph'
  | 'security'
  | 'corpus'
  | 'raw';

function asArray(v: unknown): any[] {
  return Array.isArray(v) ? v : [];
}

function chunkText(c: any): string {
  return c?.text || c?.content || '';
}

function chunkScore(c: any): number | null {
  const s = c?.score ?? c?.relevance_score ?? c?.rrf_score;
  return typeof s === 'number' ? s : null;
}

function getSteps(trace: TraceData | undefined): any[] {
  if (!trace) return [];
  if (Array.isArray(trace.steps) && trace.steps.length) return trace.steps;
  if (Array.isArray(trace.agent?.steps)) return trace.agent.steps;
  return [];
}

function getChunks(trace: TraceData | undefined): any[] {
  if (!trace) return [];
  if (Array.isArray(trace.retrieved_chunks) && trace.retrieved_chunks.length) {
    return trace.retrieved_chunks;
  }
  if (Array.isArray(trace.chunks) && trace.chunks.length) return trace.chunks;
  if (Array.isArray(trace.candidate_chunks) && trace.candidate_chunks.length) {
    return trace.candidate_chunks;
  }
  return [];
}

function getUsage(trace: TraceData | undefined) {
  const u = trace?.usage || trace?.cost;
  if (!u) return null;
  return {
    input: u.prompt_tokens ?? u.input_tokens ?? u.inputTokens ?? null,
    output: u.completion_tokens ?? u.output_tokens ?? u.outputTokens ?? null,
    total: u.total_tokens ?? null,
    cost: u.totalCost ?? u.total_cost ?? null,
  };
}

function getLatencyMs(trace: TraceData | undefined): number | null {
  if (!trace) return null;
  if (typeof trace.latency === 'number') return trace.latency;
  if (typeof trace.elapsed_seconds === 'number') return Math.round(trace.elapsed_seconds * 1000);
  return null;
}

function JsonBlock({ value, maxHeight = 'max-h-64' }: { value: unknown; maxHeight?: string }) {
  return (
    <pre
      className={clsx(
        'text-[11px] leading-relaxed text-muted font-mono bg-panel border border-line rounded-lg p-3 overflow-auto whitespace-pre-wrap break-words',
        maxHeight
      )}
    >
      {typeof value === 'string' ? value : JSON.stringify(value, null, 2)}
    </pre>
  );
}

function Metric({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="bg-panel border border-line rounded-lg p-3">
      <div className="text-[10px] uppercase tracking-wide text-muted mb-1">{label}</div>
      <div className="text-sm font-mono text-text">{value ?? '—'}</div>
    </div>
  );
}

export function Inspector({ lastResponse, selectedLevel }: InspectorProps) {
  const showCorpus = CORPUS_LEVELS.has(selectedLevel);
  const [activeTab, setActiveTab] = useState<TabKey>('overview');
  const [expandedChunks, setExpandedChunks] = useState<Set<number>>(new Set([0]));
  const [expandedSteps, setExpandedSteps] = useState<Set<number>>(new Set());

  const trace = lastResponse?.trace;
  const steps = useMemo(() => getSteps(trace), [trace]);
  const chunks = useMemo(() => getChunks(trace), [trace]);
  const messages = asArray(trace?.messages);
  const usage = getUsage(trace);
  const latency = getLatencyMs(trace);

  const tabs = useMemo(() => {
    const base: Array<{ key: TabKey; label: string; icon: typeof Activity; count?: number }> = [
      { key: 'overview', label: 'Overview', icon: Activity },
      { key: 'timeline', label: 'Timeline', icon: ListOrdered, count: steps.length },
      { key: 'chunks', label: 'Chunks', icon: Database, count: chunks.length },
      { key: 'prompt', label: 'Prompt', icon: FileText },
      { key: 'messages', label: 'Msgs', icon: Bot, count: messages.length },
    ];
    if (trace?.graph) {
      base.push({ key: 'graph', label: 'Graph', icon: Network });
    }
    if (trace?.security) {
      base.push({
        key: 'security',
        label: 'Security',
        icon: Shield,
        count: asArray(trace.security?.checks).length || undefined,
      });
    }
    if (showCorpus) {
      base.push({ key: 'corpus', label: 'Corpus', icon: FileStack });
    }
    base.push({ key: 'raw', label: 'Raw', icon: Code2 });
    return base;
  }, [steps.length, chunks.length, messages.length, trace?.graph, trace?.security, showCorpus]);

  useEffect(() => {
    if (!tabs.some((t) => t.key === activeTab)) {
      setActiveTab(showCorpus && !lastResponse ? 'corpus' : 'overview');
    }
  }, [tabs, activeTab, showCorpus, lastResponse]);

  useEffect(() => {
    setExpandedSteps(new Set(steps.map((_, i) => i)));
  }, [lastResponse]);

  const toggleChunk = (index: number) => {
    setExpandedChunks((prev) => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  };

  const toggleStep = (index: number) => {
    setExpandedSteps((prev) => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  };

  const renderOverview = () => {
    if (!trace && !lastResponse) {
      return (
        <div className="p-6 text-center text-muted">
          <Activity className="w-10 h-10 mx-auto mb-3 opacity-40" />
          <p className="text-sm">Send a message to stream every agent step here.</p>
          {showCorpus && (
            <p className="text-xs mt-2">
              Or open the <button type="button" className="text-accent underline" onClick={() => setActiveTab('corpus')}>Corpus</button> tab to browse / upload filings.
            </p>
          )}
        </div>
      );
    }

    const skip = new Set([
      'steps',
      'retrieved_chunks',
      'chunks',
      'candidate_chunks',
      'prompt',
      'messages',
      'graph',
      'start_time',
    ]);
    const extras = Object.entries(trace || {}).filter(
      ([k, v]) => !skip.has(k) && v != null && typeof v !== 'object'
    );

    return (
      <div className="p-4 space-y-4">
        <div className="grid grid-cols-2 gap-2">
          <Metric label="Level" value={trace?.level || lastResponse?.level || selectedLevel} />
          <Metric
            label="Latency"
            value={latency != null ? `${latency} ms` : '—'}
          />
          <Metric
            label="Steps"
            value={steps.length}
          />
          <Metric
            label="Chunks"
            value={chunks.length}
          />
          {usage && (
            <>
              <Metric label="In tokens" value={usage.input ?? '—'} />
              <Metric label="Out tokens" value={usage.output ?? '—'} />
            </>
          )}
        </div>

        {lastResponse?.answer && (
          <div>
            <h4 className="text-xs uppercase tracking-wide text-muted mb-2">Answer preview</h4>
            <div className="text-sm text-text bg-panel border border-line rounded-lg p-3 whitespace-pre-wrap max-h-40 overflow-y-auto">
              {lastResponse.answer.slice(0, 600)}
              {lastResponse.answer.length > 600 ? '…' : ''}
            </div>
          </div>
        )}

        {asArray(lastResponse?.citations).length > 0 && (
          <div>
            <h4 className="text-xs uppercase tracking-wide text-muted mb-2">Citations</h4>
            <div className="flex flex-wrap gap-1.5">
              {asArray(lastResponse?.citations).map((c, i) => (
                <span key={i} className="chip text-xs">{String(c)}</span>
              ))}
            </div>
          </div>
        )}

        {extras.length > 0 && (
          <div>
            <h4 className="text-xs uppercase tracking-wide text-muted mb-2">Trace fields</h4>
            <div className="space-y-1">
              {extras.slice(0, 24).map(([k, v]) => (
                <div
                  key={k}
                  className="flex items-start justify-between gap-3 text-xs border-b border-line/60 py-1.5"
                >
                  <span className="text-muted font-mono shrink-0">{k}</span>
                  <span className="text-text font-mono text-right break-all">
                    {typeof v === 'boolean' ? String(v) : String(v)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {usage?.cost != null && (
          <div className="flex items-center gap-2 text-sm text-muted">
            <DollarSign className="w-4 h-4" />
            Cost: ${Number(usage.cost).toFixed(4)}
          </div>
        )}
      </div>
    );
  };

  const renderTimeline = () => {
    if (!steps.length) {
      return (
        <div className="p-6 text-center text-muted text-sm">
          No step log for this response yet. Run a RAG / agent level to see embed → retrieve → generate.
        </div>
      );
    }
    return (
      <div className="p-3 space-y-2">
        <p className="text-xs text-muted px-1 mb-2">
          Every logged step from this chat turn — expand for tool I/O and details.
        </p>
        {steps.map((step, index) => {
          const title =
            step.action || step.tool || step.step || step.name || `Step ${index + 1}`;
          const status = step.status || (step.success === false ? 'error' : step.success ? 'ok' : null);
          const elapsed =
            typeof step.elapsed_seconds === 'number'
              ? `${(step.elapsed_seconds * 1000).toFixed(0)} ms`
              : null;
          const detail = step.detail ?? {
            ...(step.input != null ? { input: step.input } : {}),
            ...(step.output != null ? { output: step.output } : {}),
            ...(step.query != null ? { query: step.query } : {}),
            ...(step.error != null ? { error: step.error } : {}),
            ...(step.usage != null ? { usage: step.usage } : {}),
            ...(step.results_count != null ? { results_count: step.results_count } : {}),
            ...(step.context_length != null ? { context_length: step.context_length } : {}),
          };
          const hasDetail = detail && Object.keys(detail).length > 0;

          return (
            <div key={index} className="bg-panel border border-line rounded-lg overflow-hidden">
              <button
                type="button"
                onClick={() => toggleStep(index)}
                className="w-full p-3 text-left flex items-center gap-2 hover:bg-surface/40 transition-colors"
              >
                <span className="chip text-[10px] shrink-0">#{step.step ?? index + 1}</span>
                <span className="text-sm font-medium text-text truncate flex-1">{String(title)}</span>
                {status && (
                  <span
                    className={clsx(
                      'chip text-[10px]',
                      status === 'ok' || status === 'success'
                        ? 'bg-accent/20 text-accent'
                        : 'bg-red-500/20 text-red-300'
                    )}
                  >
                    {String(status)}
                  </span>
                )}
                {elapsed && (
                  <span className="text-[10px] text-muted flex items-center gap-0.5 shrink-0">
                    <Clock className="w-3 h-3" />
                    {elapsed}
                  </span>
                )}
                {hasDetail ? (
                  expandedSteps.has(index) ? (
                    <ChevronDown className="w-4 h-4 text-muted shrink-0" />
                  ) : (
                    <ChevronRight className="w-4 h-4 text-muted shrink-0" />
                  )
                ) : null}
              </button>
              <AnimatePresence>
                {hasDetail && expandedSteps.has(index) && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    className="overflow-hidden border-t border-line"
                  >
                    <div className="p-3">
                      <JsonBlock value={detail} maxHeight="max-h-80" />
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          );
        })}
      </div>
    );
  };

  const renderChunks = () => {
    const candidates = asArray(trace?.candidate_chunks);
    const list = chunks.length ? chunks : candidates;
    if (!list.length) {
      return <div className="p-6 text-center text-muted text-sm">No retrieved chunks in this trace</div>;
    }
    return (
      <div className="p-3 space-y-2">
        {candidates.length > 0 && chunks.length > 0 && (
          <p className="text-xs text-muted px-1">
            Showing final retrieved set ({chunks.length}). Candidates before rerank: {candidates.length}
          </p>
        )}
        {list.map((chunk, index) => {
          const text = chunkText(chunk);
          const score = chunkScore(chunk);
          return (
            <div key={chunk.id || index} className="bg-panel border border-line rounded-lg">
              <button
                type="button"
                onClick={() => toggleChunk(index)}
                className="w-full p-3 text-left flex items-center gap-2 hover:bg-surface/40"
              >
                <span className="chip text-[10px]">#{chunk.rank ?? index + 1}</span>
                {score != null && (
                  <span className="chip text-[10px]">score {score.toFixed(3)}</span>
                )}
                <span className="text-xs text-muted truncate flex-1">
                  {chunk.source || chunk.heading || text.slice(0, 48)}
                </span>
                {expandedChunks.has(index) ? (
                  <ChevronDown className="w-4 h-4 text-muted" />
                ) : (
                  <ChevronRight className="w-4 h-4 text-muted" />
                )}
              </button>
              <AnimatePresence>
                {expandedChunks.has(index) && (
                  <motion.div
                    initial={{ height: 0 }}
                    animate={{ height: 'auto' }}
                    exit={{ height: 0 }}
                    className="overflow-hidden border-t border-line"
                  >
                    <div className="p-3 space-y-2">
                      {(chunk.heading || chunk.source || chunk.method) && (
                        <div className="flex flex-wrap gap-1.5 text-[10px]">
                          {chunk.heading && <span className="chip">{chunk.heading}</span>}
                          {chunk.source && <span className="chip">{chunk.source}</span>}
                          {chunk.method && <span className="chip">{chunk.method}</span>}
                          {chunk.size != null && <span className="chip">{chunk.size} chars</span>}
                        </div>
                      )}
                      <pre className="text-xs text-muted whitespace-pre-wrap font-mono">
                        {text || '(empty)'}
                      </pre>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          );
        })}
      </div>
    );
  };

  const renderTabContent = () => {
    switch (activeTab) {
      case 'overview':
        return renderOverview();
      case 'timeline':
        return renderTimeline();
      case 'chunks':
        return renderChunks();
      case 'prompt':
        return (
          <div className="p-4">
            {trace?.prompt ? (
              <JsonBlock value={trace.prompt} maxHeight="max-h-[70vh]" />
            ) : (
              <div className="text-center text-muted py-8 text-sm">No prompt captured</div>
            )}
          </div>
        );
      case 'messages':
        return (
          <div className="p-3 space-y-2">
            {messages.length === 0 ? (
              <div className="text-center text-muted py-8 text-sm">No messages in trace</div>
            ) : (
              messages.map((m, i) => (
                <div key={i} className="bg-panel border border-line rounded-lg p-3">
                  <div className="chip text-[10px] mb-2">{m.role || 'unknown'}</div>
                  <pre className="text-xs text-muted whitespace-pre-wrap font-mono">
                    {typeof m.content === 'string' ? m.content : JSON.stringify(m.content, null, 2)}
                  </pre>
                </div>
              ))
            )}
          </div>
        );
      case 'graph':
        return (
          <div className="p-4 space-y-3">
            {trace?.graph ? (
              <>
                <div className="flex gap-2 text-xs">
                  <span className="chip">nodes {asArray(trace.graph.nodes).length}</span>
                  <span className="chip">edges {asArray(trace.graph.edges).length}</span>
                </div>
                <GraphCanvas graph={trace.graph} />
              </>
            ) : (
              <div className="text-center text-muted py-8 text-sm">No graph data</div>
            )}
          </div>
        );
      case 'security':
        return (
          <div className="p-4 space-y-3">
            {trace?.security ? (
              <>
                <div className="grid grid-cols-2 gap-2">
                  <Metric label="Tier" value={trace.security.tier || '—'} />
                  <Metric label="Risk" value={trace.security.risk_level || '—'} />
                </div>
                <JsonBlock value={trace.security} maxHeight="max-h-96" />
              </>
            ) : (
              <div className="text-center text-muted py-8 text-sm">No security data</div>
            )}
          </div>
        );
      case 'corpus':
        return <CorpusBrowser />;
      case 'raw':
        return (
          <div className="p-3 space-y-3">
            <p className="text-xs text-muted px-1">
              Full backend payload for this turn (answer + citations + every trace key).
            </p>
            <JsonBlock value={lastResponse || {}} maxHeight="max-h-[75vh]" />
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className="w-[26rem] xl:w-[30rem] bg-surface border-l border-line flex flex-col h-full min-h-0">
      <div className="rail-header">
        <h2 className="display text-lg text-text leading-tight">Inspector</h2>
        <p className="text-sm text-muted mt-0.5 leading-tight">
          Step log, chunks, prompts &amp; corpus
        </p>
      </div>

      <div className="shrink-0 border-b border-line">
        <div className="flex overflow-x-auto scrollbar-thin">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const hasData =
              tab.key === 'corpus' ||
              tab.key === 'overview' ||
              tab.key === 'raw' ||
              (tab.key === 'timeline' && steps.length > 0) ||
              (tab.key === 'chunks' && chunks.length > 0) ||
              (tab.key === 'prompt' && !!trace?.prompt) ||
              (tab.key === 'messages' && messages.length > 0) ||
              (tab.key === 'graph' && !!trace?.graph) ||
              (tab.key === 'security' && !!trace?.security);

            return (
              <button
                key={tab.key}
                type="button"
                onClick={() => setActiveTab(tab.key)}
                className={clsx(
                  'flex items-center gap-1.5 px-3 py-2.5 text-xs font-medium border-b-2 transition-colors whitespace-nowrap',
                  activeTab === tab.key
                    ? 'border-accent text-accent bg-accent/5'
                    : hasData
                      ? 'border-transparent text-text hover:text-accent'
                      : 'border-transparent text-muted'
                )}
              >
                <Icon className="w-3.5 h-3.5" />
                {tab.label}
                {tab.count != null && tab.count > 0 && (
                  <span className="chip text-[10px]">{tab.count}</span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto min-h-0">{renderTabContent()}</div>
    </div>
  );
}
