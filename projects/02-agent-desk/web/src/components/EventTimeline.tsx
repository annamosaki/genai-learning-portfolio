'use client';

import { AnimatePresence, motion } from 'framer-motion';
import {
  AlertCircle,
  CheckCircle,
  ChevronDown,
  Clock,
  DollarSign,
  FileText,
  Loader2,
  MessageCircle,
  Network,
  Pause,
  Play,
  Settings,
  Shield,
  Users,
} from 'lucide-react';
import { clsx } from 'clsx';
import { useEffect, useMemo, useState, type ComponentType } from 'react';
import { formatElapsed, parseTimestamp } from '@/lib/utils';

interface Event {
  type: string;
  timestamp: string;
  agent?: string;
  data: Record<string, unknown>;
}

interface IndexedEvent {
  event: Event;
  index: number;
}

interface PhaseGroup {
  id: string;
  title: string;
  subtitle?: string;
  kind: 'setup' | 'gate' | 'agent' | 'wrap';
  icon: ComponentType<{ size?: number; className?: string }>;
  events: IndexedEvent[];
  /** For specialist row — keep research/macro/quant together visually */
  lane?: 'research' | 'macro' | 'quant' | 'risk' | 'scribe';
}

interface EventTimelineProps {
  events: Event[];
  embedded?: boolean;
}

const AGENT_ORDER = ['research', 'macro', 'quant', 'risk', 'scribe'] as const;

function eventMeta(type: string) {
  switch (type) {
    case 'agent.discovered':
      return { icon: Users, tone: 'text-accent-2' };
    case 'task.created':
      return { icon: Play, tone: 'text-accent' };
    case 'message.sent':
    case 'message.received':
      return { icon: MessageCircle, tone: 'text-accent-2' };
    case 'tool.called':
    case 'tool.returned':
      return { icon: Settings, tone: 'text-muted' };
    case 'approval.required':
      return { icon: AlertCircle, tone: 'text-orange-400' };
    case 'approval.resolved':
    case 'run.finished':
      return { icon: CheckCircle, tone: 'text-accent' };
    case 'agent.finished':
      return { icon: Pause, tone: 'text-muted' };
    case 'token.usage':
      return { icon: DollarSign, tone: 'text-muted' };
    case 'error':
      return { icon: AlertCircle, tone: 'text-red-400' };
    default:
      return { icon: Clock, tone: 'text-muted' };
  }
}

function eventTitle(event: Event) {
  switch (event.type) {
    case 'agent.discovered':
      return `${event.agent} online`;
    case 'task.created':
      return String(event.data.task || 'Task started');
    case 'message.sent':
      return `→ ${event.data.to_agent || 'agent'}`;
    case 'message.received':
      return `← ${event.data.from_agent || event.agent || 'agent'}`;
    case 'tool.called':
      return event.data.service
        ? `${event.data.tool || 'tool'} → ${event.data.service}`
        : `${event.data.tool || 'tool'}`;
    case 'tool.returned':
      return event.data.service
        ? `${event.data.tool || 'tool'} ← ${event.data.service} ✓`
        : `${event.data.tool || 'tool'} ✓`;
    case 'approval.required':
      return `${event.data.type || 'gate'} approval`;
    case 'approval.resolved':
      return `${event.data.decision || 'resolved'}`;
    case 'agent.finished':
      return 'Completed';
    case 'run.finished':
      return 'Run finished';
    case 'token.usage':
      return `${Number(event.data.total_tokens || 0).toLocaleString()} tokens`;
    case 'error':
      return 'Error';
    default:
      return event.type;
  }
}

function eventSummary(event: Event) {
  switch (event.type) {
    case 'agent.discovered':
      return String(event.data.description || 'Ready');
    case 'task.created':
      return String(event.data.question || event.data.task || '');
    case 'tool.called': {
      const svc = event.data.service_label || event.data.service;
      const tool = event.data.tool ? String(event.data.tool) : 'tool';
      const args = event.data.arguments;
      const argStr =
        args && typeof args === 'object'
          ? Object.entries(args as Record<string, unknown>)
              .map(([k, v]) => `${k}=${typeof v === 'string' ? v : JSON.stringify(v)}`)
              .join(' · ')
              .slice(0, 80)
          : String(event.data.query || event.data.ticker || '');
      return svc ? `${tool} → ${svc}${argStr ? ` · ${argStr}` : ''}` : argStr || 'Calling…';
    }
    case 'tool.returned': {
      const svc = event.data.service_label || event.data.service;
      const tool = event.data.tool ? String(event.data.tool) : 'tool';
      const transport = event.data.transport || (event.data.result as { _transport?: string } | undefined)?._transport;
      const mode = event.data.retrieval_mode || (event.data.result as { retrieval_mode?: string } | undefined)?.retrieval_mode;
      if (event.data.ok === false || event.data.error) {
        return `${tool} failed${svc ? ` (${svc})` : ''}: ${event.data.error || 'error'}`;
      }
      const bits = [tool];
      if (svc) bits.push(String(svc));
      if (mode) bits.push(String(mode));
      if (transport) bits.push(String(transport));
      const count =
        event.data.results_count ??
        (event.data.result as { results_count?: number } | undefined)?.results_count ??
        event.data.rows_count;
      if (count != null) bits.push(`${count} hits`);
      return bits.join(' · ');
    }
    case 'approval.required':
      return String(event.data.description || 'Waiting');
    case 'approval.resolved':
      return String(event.data.message || event.data.decision || '');
    case 'token.usage':
      return `$${Number(event.data.estimated_cost || 0).toFixed(4)} · ${event.data.calls ?? '?'} calls`;
    case 'run.finished':
      return String(event.data.message || '');
    case 'message.sent':
    case 'message.received':
      return String(event.data.content || event.data.message || '');
    case 'error':
      return String(event.data.message || 'Unknown error');
    default:
      return String(event.data.description || event.data.message || event.data.content || '');
  }
}

function prettyJson(value: unknown): string {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function phaseStatus(events: IndexedEvent[]): 'pending' | 'active' | 'done' | 'waiting' | 'error' {
  if (!events.length) return 'pending';
  const types = events.map((e) => e.event.type);
  if (types.some((t) => t === 'error' || (t === 'agent.finished' && events.some((e) => e.event.data?.degraded)))) {
    if (types.includes('error')) return 'error';
  }
  if (types.includes('approval.required') && !types.includes('approval.resolved')) return 'waiting';
  if (types.includes('agent.finished') || types.includes('approval.resolved') || types.includes('run.finished')) {
    // still active if unfinished tools after last finish? treat done if finished present
    const hasTask = types.includes('task.created');
    const hasFinish = types.includes('agent.finished');
    if (hasTask && !hasFinish && !types.includes('run.finished')) return 'active';
    return 'done';
  }
  if (types.includes('task.created') || types.includes('tool.called')) return 'active';
  return 'done';
}

function StatusPill({ status }: { status: ReturnType<typeof phaseStatus> }) {
  const map = {
    pending: { label: 'Pending', className: 'text-muted border-line' },
    active: { label: 'Running', className: 'text-accent border-accent/40 bg-accent/10' },
    waiting: { label: 'Waiting', className: 'text-orange-400 border-orange-400/40 bg-orange-400/10' },
    done: { label: 'Done', className: 'text-accent-2 border-accent-2/30 bg-accent-2/10' },
    error: { label: 'Error', className: 'text-red-400 border-red-400/40 bg-red-400/10' },
  } as const;
  const m = map[status];
  return (
    <span className={clsx('chip text-[10px]', m.className)}>
      {status === 'active' && <Loader2 className="w-3 h-3 animate-spin mr-1" />}
      {m.label}
    </span>
  );
}

function EventDetailPanel({ event }: { event: Event }) {
  const data = event.data || {};
  const clock = parseTimestamp(event.timestamp);

  return (
    <div className="mt-2 space-y-2.5 border-t border-line/60 pt-2.5">
      <div className="grid grid-cols-2 gap-2 text-[11px]">
        <div className="bg-void/50 border border-line rounded-md px-2 py-1.5">
          <div className="text-[10px] uppercase tracking-wide text-muted mb-0.5">Type</div>
          <div className="font-mono text-text text-[10px]">{event.type}</div>
        </div>
        <div className="bg-void/50 border border-line rounded-md px-2 py-1.5">
          <div className="text-[10px] uppercase tracking-wide text-muted mb-0.5">UTC</div>
          <div className="font-mono text-text text-[10px]">
            {clock ? clock.toISOString().replace('T', ' ').replace(/\.\d+Z$/, 'Z') : '—'}
          </div>
        </div>
      </div>

      {typeof data.content === 'string' && data.content.length > 0 && (
        <div>
          <div className="text-[10px] uppercase tracking-wide text-muted mb-1">Content</div>
          <pre className="text-[11px] font-mono text-muted whitespace-pre-wrap leading-relaxed bg-void/60 border border-line rounded-md p-2 max-h-40 overflow-y-auto">
            {data.content}
          </pre>
        </div>
      )}

      {data.arguments != null && (
        <div>
          <div className="text-[10px] uppercase tracking-wide text-muted mb-1">Arguments</div>
          <pre className="text-[11px] font-mono text-muted whitespace-pre-wrap leading-relaxed bg-void/60 border border-line rounded-md p-2 max-h-32 overflow-y-auto">
            {prettyJson(data.arguments)}
          </pre>
        </div>
      )}

      {data.result != null && (
        <div>
          <div className="text-[10px] uppercase tracking-wide text-muted mb-1">Result</div>
          <pre className="text-[11px] font-mono text-muted whitespace-pre-wrap leading-relaxed bg-void/60 border border-line rounded-md p-2 max-h-40 overflow-y-auto">
            {typeof data.result === 'string' ? data.result : prettyJson(data.result)}
          </pre>
        </div>
      )}

      <details className="text-[11px]">
        <summary className="cursor-pointer text-muted hover:text-text">Full payload</summary>
        <pre className="mt-1.5 text-[11px] font-mono text-muted whitespace-pre-wrap leading-relaxed bg-void/60 border border-line rounded-md p-2 max-h-48 overflow-y-auto">
          {prettyJson(data)}
        </pre>
      </details>
    </div>
  );
}

function EventRow({
  item,
  runStart,
  expanded,
  onToggle,
}: {
  item: IndexedEvent;
  runStart: Date | null;
  expanded: boolean;
  onToggle: () => void;
}) {
  const { event, index } = item;
  const { icon: Icon, tone } = eventMeta(event.type);
  const when = parseTimestamp(event.timestamp);
  const elapsed = formatElapsed(runStart, when);
  const summary = eventSummary(event);

  return (
    <div
      className={clsx(
        'border rounded-md transition-colors',
        expanded ? 'border-accent/35 bg-surface/80' : 'border-line/80 bg-surface/40 hover:border-accent/20'
      )}
    >
      <button
        type="button"
        onClick={onToggle}
        className="w-full flex items-start gap-2.5 p-2.5 text-left"
        aria-expanded={expanded}
      >
        <div
          className={clsx(
            'flex-shrink-0 w-7 h-7 rounded-md flex items-center justify-center bg-panel border border-line',
            tone
          )}
        >
          <Icon size={13} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-text truncate">{eventTitle(event)}</span>
            <span className="text-[10px] font-mono text-muted shrink-0" title={when?.toISOString()}>
              {elapsed}
            </span>
            <ChevronDown
              className={clsx('w-3 h-3 text-muted ml-auto shrink-0 transition-transform', expanded && 'rotate-180')}
            />
          </div>
          {summary && <p className="text-[11px] text-muted line-clamp-1 mt-0.5">{summary}</p>}
        </div>
      </button>
      <AnimatePresence initial={false}>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="px-2.5 pb-2.5">
              <EventDetailPanel event={event} />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function resolveAgent(event: Event): string | null {
  if (event.agent && AGENT_ORDER.includes(event.agent as (typeof AGENT_ORDER)[number])) {
    return event.agent;
  }
  const to = event.data?.to_agent;
  const from = event.data?.from_agent;
  if (typeof to === 'string' && AGENT_ORDER.includes(to as (typeof AGENT_ORDER)[number])) return to;
  if (typeof from === 'string' && AGENT_ORDER.includes(from as (typeof AGENT_ORDER)[number])) return from;
  return null;
}

function buildPhases(events: Event[]): PhaseGroup[] {
  const indexed: IndexedEvent[] = events.map((event, index) => ({ event, index }));

  const setup: IndexedEvent[] = [];
  const planGate: IndexedEvent[] = [];
  const memoGate: IndexedEvent[] = [];
  const byAgent: Record<string, IndexedEvent[]> = {
    research: [],
    macro: [],
    quant: [],
    risk: [],
    scribe: [],
  };
  const wrap: IndexedEvent[] = [];
  const other: IndexedEvent[] = [];

  for (const item of indexed) {
    const { event } = item;
    const gateType = String(event.data?.type || '');

    if (event.type === 'agent.discovered') {
      setup.push(item);
      continue;
    }
    if (event.type === 'approval.required' || event.type === 'approval.resolved') {
      if (gateType === 'memo') memoGate.push(item);
      else planGate.push(item);
      continue;
    }
    if (event.type === 'run.finished' || event.type === 'token.usage') {
      wrap.push(item);
      continue;
    }

    // Orchestrator broadcast without a target agent → setup
    if (
      event.agent === 'orchestrator' &&
      event.type === 'message.sent' &&
      !event.data?.to_agent
    ) {
      setup.push(item);
      continue;
    }

    const agent = resolveAgent(event);
    if (agent) {
      byAgent[agent].push(item);
      continue;
    }

    other.push(item);
  }

  const phases: PhaseGroup[] = [];

  if (setup.length) {
    phases.push({
      id: 'setup',
      title: 'Desk setup',
      subtitle: 'Discover agents & prepare run',
      kind: 'setup',
      icon: Network,
      events: setup,
    });
  }

  if (planGate.length) {
    phases.push({
      id: 'plan',
      title: 'Plan gate',
      subtitle: 'Human approval of analysis plan',
      kind: 'gate',
      icon: FileText,
      events: planGate,
    });
  }

  for (const agent of ['research', 'macro', 'quant'] as const) {
    if (byAgent[agent].length) {
      const labels = {
        research: 'Research',
        macro: 'Macro',
        quant: 'Quant',
      };
      phases.push({
        id: `agent-${agent}`,
        title: labels[agent],
        subtitle: `${byAgent[agent].filter((e) => e.event.type === 'tool.called').length} tool calls`,
        kind: 'agent',
        icon: agent === 'quant' ? Settings : agent === 'macro' ? Users : FileText,
        events: byAgent[agent],
        lane: agent,
      });
    }
  }

  if (byAgent.risk.length) {
    phases.push({
      id: 'agent-risk',
      title: 'Risk',
      subtitle: 'Integrated risk assessment',
      kind: 'agent',
      icon: Shield,
      events: byAgent.risk,
      lane: 'risk',
    });
  }

  if (byAgent.scribe.length || memoGate.length) {
    const combined = [...byAgent.scribe, ...memoGate].sort((a, b) => a.index - b.index);
    phases.push({
      id: 'scribe',
      title: 'Memo & scribe',
      subtitle: 'Final answer + memo gate',
      kind: 'agent',
      icon: FileText,
      events: combined,
      lane: 'scribe',
    });
  }

  if (other.length) {
    phases.push({
      id: 'other',
      title: 'Other',
      subtitle: 'Uncategorized events',
      kind: 'setup',
      icon: Clock,
      events: other,
    });
  }

  if (wrap.length) {
    phases.push({
      id: 'wrap',
      title: 'Complete',
      subtitle: 'Usage & final status',
      kind: 'wrap',
      icon: CheckCircle,
      events: wrap,
    });
  }

  return phases;
}

function PhaseCard({
  phase,
  runStart,
  open,
  onTogglePhase,
  expandedEvent,
  onToggleEvent,
  compact,
}: {
  phase: PhaseGroup;
  runStart: Date | null;
  open: boolean;
  onTogglePhase: () => void;
  expandedEvent: string | null;
  onToggleEvent: (key: string) => void;
  compact?: boolean;
}) {
  const status = phaseStatus(phase.events);
  const Icon = phase.icon;
  const first = phase.events[0] ? parseTimestamp(phase.events[0].event.timestamp) : null;
  const last = phase.events.length
    ? parseTimestamp(phase.events[phase.events.length - 1].event.timestamp)
    : null;
  const span =
    first && last
      ? formatElapsed(runStart, first).replace('+', '') === formatElapsed(runStart, last).replace('+', '')
        ? formatElapsed(runStart, first)
        : `${formatElapsed(runStart, first)} → ${formatElapsed(runStart, last)}`
      : '—';

  return (
    <div
      className={clsx(
        'border rounded-lg overflow-hidden bg-panel/60',
        status === 'active' && 'border-accent/35',
        status === 'waiting' && 'border-orange-400/35',
        status === 'done' && 'border-line',
        status === 'error' && 'border-red-400/35'
      )}
    >
      <button
        type="button"
        onClick={onTogglePhase}
        className="w-full flex items-center gap-3 px-3 py-2.5 text-left hover:bg-panel transition-colors"
      >
        <div className="w-8 h-8 rounded-lg bg-surface border border-line flex items-center justify-center text-accent shrink-0">
          <Icon size={15} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-semibold text-text">{phase.title}</span>
            <StatusPill status={status} />
            <span className="text-[10px] font-mono text-muted">{span}</span>
          </div>
          {!compact && phase.subtitle && (
            <p className="text-[11px] text-muted truncate mt-0.5">{phase.subtitle}</p>
          )}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className="chip text-[10px]">{phase.events.length}</span>
          <ChevronDown
            className={clsx('w-4 h-4 text-muted transition-transform', open && 'rotate-180')}
          />
        </div>
      </button>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="px-3 pb-3 space-y-1.5 border-t border-line/50 pt-2">
              {phase.events.map((item) => {
                const key = `${phase.id}-${item.index}`;
                return (
                  <EventRow
                    key={key}
                    item={item}
                    runStart={runStart}
                    expanded={expandedEvent === key}
                    onToggle={() => onToggleEvent(key)}
                  />
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default function EventTimeline({ events, embedded = false }: EventTimelineProps) {
  const [expandedEvent, setExpandedEvent] = useState<string | null>(null);
  const [openPhases, setOpenPhases] = useState<Set<string>>(new Set());

  const runStart = useMemo(() => {
    for (const ev of events) {
      const t = parseTimestamp(ev.timestamp);
      if (t) return t;
    }
    return null;
  }, [events]);

  const phases = useMemo(() => buildPhases(events), [events]);

  // Auto-open active / waiting phases; keep specialist lanes open while running
  useEffect(() => {
    setOpenPhases((prev) => {
      const next = new Set(prev);
      for (const phase of phases) {
        const st = phaseStatus(phase.events);
        if (st === 'active' || st === 'waiting') next.add(phase.id);
        // First time we see a phase, open it
        if (!prev.has(phase.id) && phase.events.length) next.add(phase.id);
      }
      return next;
    });
  }, [phases]);

  const specialistPhases = phases.filter((p) =>
    ['agent-research', 'agent-macro', 'agent-quant'].includes(p.id)
  );
  const otherPhases = phases.filter(
    (p) => !['agent-research', 'agent-macro', 'agent-quant'].includes(p.id)
  );

  // Interleave: setup, plan, then specialists row, then rest in order
  const beforeSpecialists = otherPhases.filter((p) => p.id === 'setup' || p.id === 'plan');
  const afterSpecialists = otherPhases.filter((p) => p.id !== 'setup' && p.id !== 'plan');

  const togglePhase = (id: string) => {
    setOpenPhases((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const content = (
    <div className="p-4 space-y-4">
      {phases.length === 0 ? (
        <p className="text-xs text-muted text-center py-8">No events yet — start a run to see the desk flow.</p>
      ) : (
        <>
          <div className="flex items-center justify-between gap-2">
            <p className="text-[10px] uppercase tracking-wide text-muted">
              Run flow · {events.length} events
            </p>
            <div className="flex gap-1.5">
              <button
                type="button"
                className="btn text-[10px] py-1 px-2"
                onClick={() => setOpenPhases(new Set(phases.map((p) => p.id)))}
              >
                Expand all
              </button>
              <button
                type="button"
                className="btn text-[10px] py-1 px-2"
                onClick={() => setOpenPhases(new Set())}
              >
                Collapse
              </button>
            </div>
          </div>

          {/* Vertical phase rail */}
          <div className="relative space-y-3">
            <div className="absolute left-[15px] top-3 bottom-3 w-px bg-line hidden sm:block" aria-hidden />

            {beforeSpecialists.map((phase) => (
              <div key={phase.id} className="relative sm:pl-8">
                <div className="hidden sm:flex absolute left-0 top-3 w-[30px] justify-center">
                  <div className="w-2.5 h-2.5 rounded-full bg-accent border-2 border-void" />
                </div>
                <PhaseCard
                  phase={phase}
                  runStart={runStart}
                  open={openPhases.has(phase.id)}
                  onTogglePhase={() => togglePhase(phase.id)}
                  expandedEvent={expandedEvent}
                  onToggleEvent={(key) =>
                    setExpandedEvent((cur) => (cur === key ? null : key))
                  }
                />
              </div>
            ))}

            {specialistPhases.length > 0 && (
              <div className="relative sm:pl-8">
                <div className="hidden sm:flex absolute left-0 top-3 w-[30px] justify-center">
                  <div className="w-2.5 h-2.5 rounded-full bg-accent-2 border-2 border-void" />
                </div>
                <div className="mb-2 flex items-center gap-2">
                  <span className="text-[10px] uppercase tracking-wide text-muted">
                    Parallel specialists
                  </span>
                  <span className="h-px flex-1 bg-line" />
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
                  {specialistPhases.map((phase) => (
                    <PhaseCard
                      key={phase.id}
                      phase={phase}
                      runStart={runStart}
                      open={openPhases.has(phase.id)}
                      onTogglePhase={() => togglePhase(phase.id)}
                      expandedEvent={expandedEvent}
                      onToggleEvent={(key) =>
                        setExpandedEvent((cur) => (cur === key ? null : key))
                      }
                      compact
                    />
                  ))}
                </div>
              </div>
            )}

            {afterSpecialists.map((phase) => (
              <div key={phase.id} className="relative sm:pl-8">
                <div className="hidden sm:flex absolute left-0 top-3 w-[30px] justify-center">
                  <div
                    className={clsx(
                      'w-2.5 h-2.5 rounded-full border-2 border-void',
                      phase.id === 'wrap' ? 'bg-accent' : 'bg-accent-2'
                    )}
                  />
                </div>
                <PhaseCard
                  phase={phase}
                  runStart={runStart}
                  open={openPhases.has(phase.id)}
                  onTogglePhase={() => togglePhase(phase.id)}
                  expandedEvent={expandedEvent}
                  onToggleEvent={(key) =>
                    setExpandedEvent((cur) => (cur === key ? null : key))
                  }
                />
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );

  if (embedded) return content;

  return (
    <div className="bg-surface border border-line rounded-lg h-96 overflow-hidden flex flex-col">
      <div className="px-4 py-3 border-b border-line">
        <h3 className="text-[10px] uppercase tracking-wide text-muted">Event Timeline</h3>
      </div>
      <div className="flex-1 overflow-y-auto">{content}</div>
    </div>
  );
}
