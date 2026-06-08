'use client';

import { AnimatePresence, motion } from 'framer-motion';
import {
  BarChart3,
  Brain,
  Calculator,
  Database,
  FileSearch,
  Maximize2,
  Minimize2,
  PenTool,
  RotateCcw,
  Shield,
  Sigma,
  TrendingUp,
  X,
  ZoomIn,
  ZoomOut,
} from 'lucide-react';
import { clsx } from 'clsx';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

type NodeStatus = 'idle' | 'active' | 'completed' | 'error' | 'degraded';
type NodeKind = 'core' | 'mcp' | 'local';

interface GraphEvent {
  type: string;
  agent?: string;
  data?: Record<string, unknown>;
}

interface AgentDef {
  id: string;
  name: string;
  role: string;
  x: number;
  y: number;
  icon: React.ComponentType<{ size?: number; className?: string }>;
  kind: NodeKind;
  blurb: string;
  tools?: string[];
  /** Sequence step shown as a small badge; only set on the main pipeline agents */
  step?: number;
}

interface Connection {
  from: string;
  to: string;
  kind?: 'flow' | 'tool';
}

interface AgentGraphProps {
  events: GraphEvent[];
  activeAgents: Set<string>;
  className?: string;
  expanded?: boolean;
  onExpandChange?: (expanded: boolean) => void;
}

const VB = { w: 860, h: 520 };

/**
 * Grid layout, straight rim-to-rim edges only (no bezier bowing that can
 * visually "hump" over a node that happens to sit near the path).
 *
 * Row 1 (y≈50):  PM
 * Row 2 (y≈205): RAG/Edgar ↘ Research · Macro · Yahoo · Quant ↙ Indicators
 *                (Yahoo sits in its own lane between Macro and Quant so it
 *                 never crosses the PM→Quant or PM→Macro lines above it)
 * Row 3 (y≈345): Risk
 * Row 4 (y≈450): Scribe
 */
const AGENTS: AgentDef[] = [
  {
    id: 'orchestrator',
    name: 'PM',
    role: 'Orchestrator',
    x: 430,
    y: 48,
    icon: Brain,
    kind: 'core',
    step: 1,
    blurb:
      'Plans the run, picks which specialists to call, and handles the plan/memo approval gates.',
  },
  {
    id: 'rag',
    name: 'RAG',
    role: 'Hybrid retrieval',
    x: 68,
    y: 148,
    icon: FileSearch,
    kind: 'local',
    tools: ['search_filings'],
    blurb:
      'Local hybrid RAG over indexed 10-Ks (BM25 + dense, RRF fusion). Best for NVDA / AAPL / MSFT.',
  },
  {
    id: 'edgar',
    name: 'Edgar',
    role: 'SEC filings',
    x: 68,
    y: 258,
    icon: Database,
    kind: 'mcp',
    tools: ['lookup_filings'],
    blurb: 'Live SEC filings via Edgar MCP (falls back to edgartools). Any ticker / form type.',
  },
  {
    id: 'research',
    name: 'Research',
    role: 'Fundamentals',
    x: 195,
    y: 205,
    icon: Database,
    kind: 'core',
    step: 2,
    tools: ['search_filings', 'lookup_filings'],
    blurb: 'SEC fundamentals. Calls RAG + Edgar, then writes a sourced brief for Risk & Scribe.',
  },
  {
    id: 'macro',
    name: 'Macro',
    role: 'Sector & news',
    x: 430,
    y: 205,
    icon: TrendingUp,
    kind: 'core',
    step: 2,
    tools: ['get_ticker_info', 'get_ticker_news', 'get_peer_info'],
    blurb: 'Sector / macro context from Yahoo news and peer data.',
  },
  {
    id: 'yahoo',
    name: 'Yahoo',
    role: 'Market data',
    x: 560,
    y: 205,
    icon: BarChart3,
    kind: 'mcp',
    tools: ['get_ticker_info', 'get_ticker_news', 'get_peer_info', 'load_price_history'],
    blurb:
      'Yahoo Finance MCP (falls back to yfinance). Serves both Macro (news/peers) and Quant (OHLCV).',
  },
  {
    id: 'quant',
    name: 'Quant',
    role: 'Technicals',
    x: 690,
    y: 205,
    icon: Calculator,
    kind: 'core',
    step: 2,
    tools: ['load_price_history', 'compute_indicators'],
    blurb: 'Price & technicals. Loads OHLCV from Yahoo, then computes local indicators.',
  },
  {
    id: 'indicators',
    name: 'Indicators',
    role: 'Local math',
    x: 800,
    y: 205,
    icon: Sigma,
    kind: 'local',
    tools: ['compute_indicators'],
    blurb: 'Local RSI, MACD, returns, and volatility computed on price history.',
  },
  {
    id: 'risk',
    name: 'Risk',
    role: 'Risk scoring',
    x: 430,
    y: 345,
    icon: Shield,
    kind: 'core',
    step: 3,
    blurb: 'Merges Research, Macro, and Quant into a risk view (LLM only — no tools).',
  },
  {
    id: 'scribe',
    name: 'Scribe',
    role: 'Memo writer',
    x: 430,
    y: 455,
    icon: PenTool,
    kind: 'core',
    step: 4,
    blurb: 'Writes the final investment memo. Subject to memo approval.',
  },
];

const STATIC_EDGES: Connection[] = [
  { from: 'orchestrator', to: 'research', kind: 'flow' },
  { from: 'orchestrator', to: 'macro', kind: 'flow' },
  { from: 'orchestrator', to: 'quant', kind: 'flow' },
  { from: 'rag', to: 'research', kind: 'tool' },
  { from: 'edgar', to: 'research', kind: 'tool' },
  { from: 'yahoo', to: 'macro', kind: 'tool' },
  { from: 'yahoo', to: 'quant', kind: 'tool' },
  { from: 'indicators', to: 'quant', kind: 'tool' },
  { from: 'research', to: 'risk', kind: 'flow' },
  { from: 'macro', to: 'risk', kind: 'flow' },
  { from: 'quant', to: 'risk', kind: 'flow' },
  { from: 'risk', to: 'scribe', kind: 'flow' },
];

const TOOL_TO_SERVICE: Record<string, string> = {
  search_filings: 'rag',
  lookup_filings: 'edgar',
  get_ticker_info: 'yahoo',
  get_ticker_news: 'yahoo',
  get_peer_info: 'yahoo',
  load_price_history: 'yahoo',
  compute_indicators: 'indicators',
};

const SERVICE_IDS = new Set(['rag', 'edgar', 'yahoo', 'indicators']);

function serviceFromEvent(event: GraphEvent): string | null {
  const data = event.data || {};
  if (typeof data.service === 'string' && AGENTS.some((a) => a.id === data.service)) {
    return data.service;
  }
  if (typeof data.tool === 'string' && TOOL_TO_SERVICE[data.tool]) {
    return TOOL_TO_SERVICE[data.tool];
  }
  return null;
}

function nodeColor(status: NodeStatus, kind: NodeKind) {
  if (status === 'active') return { fill: '#3dffb5', stroke: '#3dffb5' };
  if (status === 'error') return { fill: 'rgba(248,113,113,0.2)', stroke: '#f87171' };
  if (status === 'degraded') return { fill: 'rgba(251,191,36,0.18)', stroke: '#fbbf24' };
  if (status === 'completed') return { fill: 'rgba(61,255,181,0.15)', stroke: '#3dffb5' };
  if (kind === 'mcp') return { fill: '#0b1018', stroke: 'rgba(148,163,184,0.45)' };
  if (kind === 'local') return { fill: '#0d1520', stroke: 'rgba(76,201,255,0.45)' };
  return { fill: '#111823', stroke: 'rgba(148,163,184,0.35)' };
}

function kindBadge(kind: NodeKind) {
  if (kind === 'mcp') return 'MCP';
  if (kind === 'local') return 'LOCAL';
  return 'AGENT';
}

function nodeRadius(kind: NodeKind) {
  return kind === 'core' ? 27 : 20;
}

/**
 * Always a straight line between node rims, along the direct vector between
 * centers. This guarantees the line never bows toward — or "humps" over —
 * any other node, regardless of layout.
 */
function edgePath(
  from: { x: number; y: number },
  to: { x: number; y: number },
  fromR: number,
  toR: number
): string {
  const dx = to.x - from.x;
  const dy = to.y - from.y;
  const dist = Math.sqrt(dx * dx + dy * dy) || 1;
  const ux = dx / dist;
  const uy = dy / dist;
  const x1 = from.x + ux * fromR;
  const y1 = from.y + uy * fromR;
  const x2 = to.x - ux * toR;
  const y2 = to.y - uy * toR;
  return `M ${x1} ${y1} L ${x2} ${y2}`;
}

function statusLabel(s: NodeStatus) {
  if (s === 'degraded') return 'fallback';
  return s;
}

export default function AgentGraph({
  events,
  activeAgents,
  className,
  expanded = false,
  onExpandChange,
}: AgentGraphProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [dragging, setDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [pulseEdges, setPulseEdges] = useState<Connection[]>([]);

  const runFinished = events.some((e) => e.type === 'run.finished');

  const serviceState = useMemo(() => {
    const inFlight = new Set<string>();
    const completed = new Set<string>();
    const degraded = new Set<string>();
    const errored = new Set<string>();
    const lastTool = new Map<string, string>();
    const lastTransport = new Map<string, string>();
    const lastMode = new Map<string, string>();

    for (const event of events) {
      const service = serviceFromEvent(event);
      if (!service) continue;
      const tool = typeof event.data?.tool === 'string' ? event.data.tool : undefined;
      const transport =
        (typeof event.data?.transport === 'string' && event.data.transport) ||
        (typeof (event.data?.result as { _transport?: string } | undefined)?._transport ===
          'string' &&
          (event.data?.result as { _transport?: string })._transport) ||
        undefined;
      const mode =
        typeof event.data?.retrieval_mode === 'string'
          ? event.data.retrieval_mode
          : typeof (event.data?.result as { retrieval_mode?: string } | undefined)
                ?.retrieval_mode === 'string'
            ? (event.data?.result as { retrieval_mode?: string }).retrieval_mode
            : undefined;

      if (tool) lastTool.set(service, tool);
      if (transport) lastTransport.set(service, transport);
      if (mode) lastMode.set(service, mode);

      if (event.type === 'tool.called') {
        inFlight.add(service);
        errored.delete(service);
      }
      if (event.type === 'tool.returned') {
        inFlight.delete(service);
        completed.add(service);
        const ok = event.data?.ok !== false;
        const isDegraded =
          Boolean(event.data?.degraded) ||
          (typeof transport === 'string' && transport.endsWith('_direct'));
        if (!ok) errored.add(service);
        else if (isDegraded) degraded.add(service);
      }
    }

    return { inFlight, completed, degraded, errored, lastTool, lastTransport, lastMode };
  }, [events]);

  const getStatus = useCallback(
    (agentId: string): NodeStatus => {
      if (SERVICE_IDS.has(agentId)) {
        if (serviceState.inFlight.has(agentId)) return 'active';
        if (serviceState.errored.has(agentId)) return 'error';
        if (serviceState.degraded.has(agentId)) return 'degraded';
        if (serviceState.completed.has(agentId)) return 'completed';
        return 'idle';
      }

      if (agentId === 'orchestrator') {
        if (runFinished) return 'completed';
        const hasActivity =
          events.length > 0 &&
          (activeAgents.size > 0 ||
            events.some(
              (e) =>
                e.type === 'approval.required' ||
                e.type === 'message.sent' ||
                e.type === 'agent.discovered'
            ));
        return hasActivity ? 'active' : 'idle';
      }

      if (activeAgents.has(agentId)) return 'active';
      for (let i = events.length - 1; i >= 0; i -= 1) {
        const e = events[i];
        if (e.type === 'agent.finished' && e.agent === agentId) {
          return e.data?.degraded ? 'degraded' : 'completed';
        }
      }
      return 'idle';
    },
    [events, activeAgents, runFinished, serviceState]
  );

  useEffect(() => {
    const next: Connection[] = [];
    for (const event of events.slice(-12)) {
      if (event.type === 'message.sent' && event.data?.to_agent) {
        next.push({
          from: event.agent || 'orchestrator',
          to: String(event.data.to_agent),
          kind: 'flow',
        });
      }
      if (event.type === 'tool.called' || event.type === 'tool.returned') {
        const service = serviceFromEvent(event);
        const agent = event.agent;
        if (service && agent) next.push({ from: service, to: agent, kind: 'tool' });
      }
    }
    setPulseEdges(next);
    const t = setTimeout(() => setPulseEdges([]), 2400);
    return () => clearTimeout(t);
  }, [events]);

  const stats = useMemo(() => {
    const active = AGENTS.filter((a) => getStatus(a.id) === 'active').length;
    const done = AGENTS.filter((a) => getStatus(a.id) === 'completed').length;
    const toolsUsed = new Set(
      events
        .filter((e) => e.type === 'tool.called' || e.type === 'tool.returned')
        .map((e) => String(e.data?.tool || ''))
        .filter(Boolean)
    ).size;
    return { active, done, toolsUsed };
  }, [getStatus, events]);

  const selected = AGENTS.find((a) => a.id === selectedId) || null;

  const selectedLive = useMemo(() => {
    if (!selected) return null;
    if (SERVICE_IDS.has(selected.id)) {
      return {
        tool: serviceState.lastTool.get(selected.id),
        transport: serviceState.lastTransport.get(selected.id),
        mode: serviceState.lastMode.get(selected.id),
      };
    }
    const tools = events
      .filter(
        (e) =>
          (e.type === 'tool.called' || e.type === 'tool.returned') &&
          e.agent === selected.id &&
          typeof e.data?.tool === 'string'
      )
      .map((e) => String(e.data!.tool));
    return { tools: [...new Set(tools)].slice(-5) };
  }, [selected, serviceState, events]);

  const relatedEdgeKeys = useMemo(() => {
    if (!selectedId) return new Set<string>();
    const keys = new Set<string>();
    for (const e of STATIC_EDGES) {
      if (e.from === selectedId || e.to === selectedId) keys.add(`${e.from}->${e.to}`);
    }
    return keys;
  }, [selectedId]);

  const resetView = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  };

  const onWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    setZoom((z) => Math.min(2.5, Math.max(0.55, z - e.deltaY * 0.0015)));
  };

  const onPointerDown = (e: React.PointerEvent) => {
    if ((e.target as Element).closest('[data-agent-node],[data-info-bubble]')) return;
    setSelectedId(null);
    setDragging(true);
    setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
    (e.currentTarget as Element).setPointerCapture(e.pointerId);
  };

  const onPointerMove = (e: React.PointerEvent) => {
    if (!dragging) return;
    setPan({ x: e.clientX - dragStart.x, y: e.clientY - dragStart.y });
  };

  const onPointerUp = (e: React.PointerEvent) => {
    setDragging(false);
    try {
      (e.currentTarget as Element).releasePointerCapture(e.pointerId);
    } catch {
      /* ignore */
    }
  };

  const bubblePlacement = useMemo(() => {
    if (!selected) return null;
    const placeRight = selected.x < VB.w - 280;
    return {
      x: placeRight ? selected.x + 40 : selected.x - 256,
      y: Math.max(8, Math.min(VB.h - 220, selected.y - 40)),
    };
  }, [selected]);

  const byId = useMemo(() => new Map(AGENTS.map((a) => [a.id, a])), []);

  const renderGraph = () => (
    <div className={clsx('relative flex flex-col min-h-0 bg-panel/30', className)}>
      <div className="absolute top-2 left-3 z-10 text-[10px] text-muted tracking-wide pointer-events-none">
        1 Plan → 2 Specialists (parallel) → 3 Risk → 4 Memo
      </div>

      <div className="absolute top-2 right-2 z-20 flex items-center gap-1">
        <button type="button" className="btn text-xs p-1.5" onClick={() => setZoom((z) => Math.min(2.5, z + 0.15))} title="Zoom in">
          <ZoomIn className="w-3.5 h-3.5" />
        </button>
        <button type="button" className="btn text-xs p-1.5" onClick={() => setZoom((z) => Math.max(0.55, z - 0.15))} title="Zoom out">
          <ZoomOut className="w-3.5 h-3.5" />
        </button>
        <button type="button" className="btn text-xs p-1.5" onClick={resetView} title="Reset view">
          <RotateCcw className="w-3.5 h-3.5" />
        </button>
        {onExpandChange && (
          <button
            type="button"
            className="btn text-xs p-1.5"
            onClick={() => onExpandChange(!expanded)}
            title={expanded ? 'Collapse' : 'Expand graph'}
          >
            {expanded ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
          </button>
        )}
      </div>

      <svg
        ref={svgRef}
        viewBox={`0 0 ${VB.w} ${VB.h}`}
        preserveAspectRatio="xMidYMid meet"
        className={clsx(
          'w-full flex-1 min-h-[200px] touch-none select-none',
          dragging ? 'cursor-grabbing' : 'cursor-grab'
        )}
        onWheel={onWheel}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerLeave={onPointerUp}
      >
        <defs>
          <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          <marker
            id="arrow-flow"
            viewBox="0 0 14 14"
            refX="12"
            refY="7"
            markerWidth="13"
            markerHeight="13"
            markerUnits="userSpaceOnUse"
            orient="auto"
          >
            <circle cx="7" cy="7" r="6.2" fill="#0b1018" />
            <path d="M 3.2 3.2 L 11.5 7 L 3.2 10.8 Z" fill="#c5d0e0" stroke="#0b1018" strokeWidth="0.6" />
          </marker>
          <marker
            id="arrow-tool"
            viewBox="0 0 14 14"
            refX="12"
            refY="7"
            markerWidth="12"
            markerHeight="12"
            markerUnits="userSpaceOnUse"
            orient="auto"
          >
            <circle cx="7" cy="7" r="6.2" fill="#0b1018" />
            <path d="M 3.2 3.2 L 11.5 7 L 3.2 10.8 Z" fill="#4cc9ff" stroke="#0b1018" strokeWidth="0.6" />
          </marker>
          <marker
            id="arrow-pulse"
            viewBox="0 0 14 14"
            refX="12"
            refY="7"
            markerWidth="13"
            markerHeight="13"
            markerUnits="userSpaceOnUse"
            orient="auto"
          >
            <circle cx="7" cy="7" r="6.2" fill="#04110c" />
            <path d="M 3.2 3.2 L 11.5 7 L 3.2 10.8 Z" fill="#3dffb5" stroke="#04110c" strokeWidth="0.6" />
          </marker>
        </defs>

        <g transform={`translate(${pan.x} ${pan.y}) scale(${zoom})`}>
          <rect x={0} y={0} width={VB.w} height={VB.h} fill="transparent" />

          {STATIC_EDGES.map((edge) => {
            const from = byId.get(edge.from);
            const to = byId.get(edge.to);
            if (!from || !to) return null;
            const key = `${edge.from}->${edge.to}`;
            const related = !selectedId || relatedEdgeKeys.has(key);
            const isTool = edge.kind === 'tool';
            const d = edgePath(from, to, nodeRadius(from.kind), nodeRadius(to.kind));
            const stroke = related
              ? isTool
                ? 'rgba(76,201,255,0.85)'
                : 'rgba(197,208,224,0.75)'
              : 'rgba(148,163,184,0.1)';
            return (
              <g key={key} opacity={related ? 1 : 0.35}>
                {isTool && related && (
                  <path d={d} fill="none" stroke="rgba(76,201,255,0.16)" strokeWidth={3} />
                )}
                <path
                  d={d}
                  fill="none"
                  stroke={stroke}
                  strokeWidth={isTool ? 1.8 : 2}
                  strokeLinecap="round"
                  strokeDasharray={isTool ? '5 4' : undefined}
                  markerEnd={isTool ? 'url(#arrow-tool)' : 'url(#arrow-flow)'}
                />
              </g>
            );
          })}

          {pulseEdges.map((edge, i) => {
            const from = byId.get(edge.from);
            const to = byId.get(edge.to);
            if (!from || !to) return null;
            return (
              <motion.path
                key={`pulse-${edge.from}-${edge.to}-${i}`}
                d={edgePath(from, to, nodeRadius(from.kind), nodeRadius(to.kind))}
                fill="none"
                stroke="#3dffb5"
                strokeWidth={2.3}
                strokeLinecap="round"
                markerEnd="url(#arrow-pulse)"
                initial={{ pathLength: 0, opacity: 0.95 }}
                animate={{ pathLength: 1, opacity: 0.15 }}
                transition={{ duration: 0.55 }}
              />
            );
          })}

          {AGENTS.map((agent) => {
            const status = getStatus(agent.id);
            const colors = nodeColor(status, agent.kind);
            const Icon = agent.icon;
            const isSelected = selectedId === agent.id;
            const r = nodeRadius(agent.kind);
            const dimmed =
              Boolean(selectedId) &&
              !isSelected &&
              !relatedEdgeKeys.has(`${selectedId}->${agent.id}`) &&
              !relatedEdgeKeys.has(`${agent.id}->${selectedId}`);

            return (
              <g
                key={agent.id}
                data-agent-node
                transform={`translate(${agent.x}, ${agent.y})`}
                opacity={dimmed ? 0.28 : 1}
                onClick={(e) => {
                  e.stopPropagation();
                  setSelectedId((id) => (id === agent.id ? null : agent.id));
                }}
                className="cursor-pointer"
              >
                {status === 'active' && (
                  <circle r={r + 9} fill="none" stroke="#3dffb5" strokeWidth={1.4} opacity={0.35}>
                    <animate
                      attributeName="r"
                      values={`${r + 5};${r + 12};${r + 5}`}
                      dur="1.4s"
                      repeatCount="indefinite"
                    />
                    <animate
                      attributeName="opacity"
                      values="0.5;0.12;0.5"
                      dur="1.4s"
                      repeatCount="indefinite"
                    />
                  </circle>
                )}

                <circle
                  r={r}
                  fill={colors.fill}
                  stroke={isSelected ? '#4cc9ff' : colors.stroke}
                  strokeWidth={isSelected ? 2.4 : 1.5}
                  filter={status === 'active' ? 'url(#glow)' : undefined}
                  strokeDasharray={agent.kind !== 'core' ? '3 2' : undefined}
                />

                {agent.step != null && (
                  <g transform={`translate(${-r - 2}, ${-r - 2})`}>
                    <circle r={8} fill="#0b1018" stroke="rgba(148,163,184,0.5)" strokeWidth={1} />
                    <text
                      textAnchor="middle"
                      dominantBaseline="central"
                      fontSize={9}
                      fontWeight={700}
                      fill="#c5d0e0"
                    >
                      {agent.step}
                    </text>
                  </g>
                )}

                <foreignObject x={-10} y={-10} width={20} height={20} className="pointer-events-none">
                  <div className="flex items-center justify-center w-full h-full">
                    <Icon
                      size={14}
                      className={
                        status === 'active'
                          ? 'text-void'
                          : status === 'completed'
                            ? 'text-accent'
                            : status === 'error'
                              ? 'text-red-400'
                              : status === 'degraded'
                                ? 'text-amber-400'
                                : 'text-muted'
                      }
                    />
                  </div>
                </foreignObject>

                <text
                  y={r + 13}
                  textAnchor="middle"
                  fill={status === 'active' ? '#3dffb5' : '#c5d0e0'}
                  fontSize={11}
                  fontWeight={600}
                  className="pointer-events-none"
                >
                  {agent.name}
                </text>
                <text
                  y={r + 24}
                  textAnchor="middle"
                  fill={agent.kind === 'local' ? '#4cc9ff' : '#8b9bb4'}
                  fontSize={8}
                  className="pointer-events-none"
                >
                  {kindBadge(agent.kind)}
                </text>
              </g>
            );
          })}

          <AnimatePresence>
            {selected && bubblePlacement && (
              <foreignObject
                key={selected.id}
                x={bubblePlacement.x}
                y={bubblePlacement.y}
                width={248}
                height={220}
                style={{ overflow: 'visible' }}
              >
                <motion.div
                  data-info-bubble
                  initial={{ opacity: 0, y: 6, scale: 0.96 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.96 }}
                  transition={{ duration: 0.14 }}
                  className="pointer-events-auto w-[236px] rounded-lg border border-line bg-surface/95 backdrop-blur-sm shadow-xl p-3 text-left"
                  onClick={(e) => e.stopPropagation()}
                  onPointerDown={(e) => e.stopPropagation()}
                >
                  <div className="flex items-start justify-between gap-2 mb-1.5">
                    <div className="min-w-0">
                      <div className="text-sm font-semibold text-text truncate">{selected.name}</div>
                      <div className="text-[11px] text-muted">{selected.role}</div>
                    </div>
                    <button
                      type="button"
                      className="p-0.5 rounded text-muted hover:text-text"
                      onClick={() => setSelectedId(null)}
                      aria-label="Close"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>

                  <div className="flex flex-wrap gap-1.5 mb-2">
                    <span className="chip capitalize text-[10px]">
                      {statusLabel(getStatus(selected.id))}
                    </span>
                    <span className="chip text-[10px]">{kindBadge(selected.kind)}</span>
                    {selected.step != null && (
                      <span className="chip text-[10px]">Step {selected.step}</span>
                    )}
                  </div>

                  <p className="text-[11px] leading-relaxed text-muted mb-2">{selected.blurb}</p>

                  {selected.tools && selected.tools.length > 0 && (
                    <div className="mb-1.5">
                      <div className="text-[9px] uppercase tracking-wide text-muted mb-1">Tools</div>
                      <div className="flex flex-wrap gap-1">
                        {selected.tools.map((t) => (
                          <span
                            key={t}
                            className="px-1.5 py-0.5 rounded bg-void/70 border border-line font-mono text-[10px] text-accent"
                          >
                            {t}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {selectedLive?.tool && (
                    <div className="text-[10px] text-muted border-t border-line pt-1.5 mt-1">
                      Last call:{' '}
                      <span className="text-text font-mono">{selectedLive.tool}</span>
                      {selectedLive.transport ? (
                        <span> · {selectedLive.transport}</span>
                      ) : null}
                      {selectedLive.mode ? <span> · {selectedLive.mode}</span> : null}
                    </div>
                  )}
                  {selectedLive?.tools && selectedLive.tools.length > 0 && (
                    <div className="text-[10px] text-muted border-t border-line pt-1.5 mt-1">
                      Used this run:{' '}
                      <span className="text-text font-mono">{selectedLive.tools.join(', ')}</span>
                    </div>
                  )}
                </motion.div>
              </foreignObject>
            )}
          </AnimatePresence>
        </g>
      </svg>

      <div className="shrink-0 border-t border-line px-3 py-2 flex flex-wrap items-center justify-between gap-2 bg-surface/80 text-[11px]">
        <div className="flex flex-wrap items-center gap-3 text-muted">
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-accent" /> Active ({stats.active})
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-accent/30 border border-accent/50" /> Done ({stats.done})
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-3 border-t border-dashed border-[#4cc9ff]/70" /> Tool
          </span>
          {stats.toolsUsed > 0 && (
            <span className="text-accent/80">Tools used: {stats.toolsUsed}</span>
          )}
        </div>
        <span className="text-muted">Click a node for details</span>
      </div>
    </div>
  );

  return (
    <>
      {renderGraph()}
      {expanded && (
        <motion.div
          className="fixed inset-0 z-50 bg-black/85 flex flex-col p-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          onClick={() => onExpandChange?.(false)}
        >
          <motion.div
            className="flex-1 bg-surface border border-line rounded-lg overflow-hidden flex flex-col min-h-0"
            initial={{ scale: 0.97 }}
            animate={{ scale: 1 }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="px-4 py-3 border-b border-line flex items-center justify-between">
              <div>
                <h2 className="display text-base text-text">Agent Network</h2>
                <p className="text-xs text-muted">1 Plan → 2 Specialists → 3 Risk → 4 Memo</p>
              </div>
              <button type="button" className="btn" onClick={() => onExpandChange?.(false)}>
                Close
              </button>
            </div>
            {renderGraph()}
          </motion.div>
        </motion.div>
      )}
    </>
  );
}
