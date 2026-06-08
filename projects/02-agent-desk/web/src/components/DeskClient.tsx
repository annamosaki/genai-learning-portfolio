'use client';

import { useState } from 'react';
import { clsx } from 'clsx';
import { motion } from 'framer-motion';
import { Loader2, Network, Play, Zap } from 'lucide-react';

import AgentGraph from '@/components/AgentGraph';
import ApprovalDrawer from '@/components/ApprovalDrawer';
import { BackToPortfolio } from '@/components/BackToPortfolio';
import { RunOutputPanel } from '@/components/RunOutputPanel';
import { apiUrl } from '@/lib/api';

interface Event {
  type: string;
  timestamp: string;
  agent?: string;
  data: Record<string, unknown>;
}

interface ApprovalGate {
  gate_id: string;
  type: string;
  description: string;
  content: string;
}

const EXAMPLE_TICKERS = ['NVDA', 'AAPL', 'MSFT', 'TSLA'];

export function DeskClient() {
  const [ticker, setTicker] = useState('NVDA');
  const [question, setQuestion] = useState('Provide a comprehensive investment analysis');
  const [isRunning, setIsRunning] = useState(false);
  const [events, setEvents] = useState<Event[]>([]);
  const [currentApproval, setCurrentApproval] = useState<ApprovalGate | null>(null);
  const [isApprovalOpen, setIsApprovalOpen] = useState(false);
  const [isProcessingApproval, setIsProcessingApproval] = useState(false);
  const [finalMemo, setFinalMemo] = useState<string | null>(null);
  const [runId, setRunId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'timeline' | 'memo'>('timeline');
  const [graphExpanded, setGraphExpanded] = useState(false);
  const [graphTall, setGraphTall] = useState(false);

  const activeAgents = new Set<string>();
  for (const event of events) {
    if (event.type === 'task.created' && event.agent) {
      activeAgents.add(event.agent);
    }
    if (event.type === 'agent.finished' && event.agent) {
      activeAgents.delete(event.agent);
    }
  }

  const tokenEvent = [...events].reverse().find((e) => e.type === 'token.usage');
  const tokenData = tokenEvent?.data as
    | { total_tokens?: number; estimated_cost?: number }
    | undefined;

  const startAnalysis = async () => {
    if (!ticker.trim()) return;

    setIsRunning(true);
    setEvents([]);
    setFinalMemo(null);
    setCurrentApproval(null);
    setActiveTab('timeline');

    try {
      const response = await fetch(apiUrl('/api/run'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ticker: ticker.trim().toUpperCase(), question }),
      });

      if (!response.ok) {
        let detail = 'Failed to start analysis';
        try {
          const errBody = await response.json();
          if (errBody?.detail) {
            detail = typeof errBody.detail === 'string' ? errBody.detail : JSON.stringify(errBody.detail);
          }
        } catch {
          /* ignore */
        }
        throw new Error(detail);
      }

      const result = await response.json();
      setRunId(result.run_id);

      const eventSource = new EventSource(apiUrl(`/api/run/${result.run_id}/stream`));

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'keepalive') return;

          setEvents((prev) => [...prev, data]);

          if (data.type === 'approval.required') {
            setCurrentApproval({
              gate_id: data.data.gate_id,
              type: data.data.type,
              description: data.data.description,
              content: data.data.content,
            });
            setIsProcessingApproval(false);
            setIsApprovalOpen(true);
            // Show draft memo while waiting on memo gate (incl. after Edit reloops)
            if (data.data.type === 'memo' && data.data.content) {
              setFinalMemo(data.data.content);
            }
          }

          if (data.type === 'approval.resolved') {
            setIsProcessingApproval(false);
            setIsApprovalOpen(false);
            setCurrentApproval(null);
          }

          if (data.type === 'run.finished') {
            setIsRunning(false);
            eventSource.close();

            if (data.data.memo_available) {
              fetchFinalMemo(result.run_id);
              setActiveTab('memo');
            }
          }
        } catch (err) {
          console.error('Error parsing SSE event:', err);
        }
      };

      eventSource.onerror = () => {
        setIsRunning(false);
        eventSource.close();
      };
    } catch (error) {
      console.error('Error starting analysis:', error);
      const message = error instanceof Error ? error.message : 'Failed to start analysis';
      setEvents((prev) => [
        ...prev,
        {
          type: 'error',
          timestamp: new Date().toISOString(),
          data: { message },
        },
      ]);
      setIsRunning(false);
    }
  };

  const fetchFinalMemo = async (id: string) => {
    try {
      const response = await fetch(apiUrl(`/api/run/${id}`));
      if (response.ok) {
        const runState = await response.json();
        if (runState.final_memo) {
          setFinalMemo(runState.final_memo);
        }
      }
    } catch (error) {
      console.error('Error fetching memo:', error);
    }
  };

  const handleApproval = async (
    decision: 'approve' | 'edit' | 'deny',
    message?: string
  ) => {
    if (!currentApproval || !runId) return;

    setIsProcessingApproval(true);

    try {
      const response = await fetch(apiUrl(`/api/run/${runId}/approve`), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tool_call_id: currentApproval.gate_id,
          decision,
          message,
        }),
      });

      if (response.ok) {
        setIsApprovalOpen(false);
        setCurrentApproval(null);
      } else {
        // Allow retry if the approve call failed
        console.error('Approval rejected by API', await response.text());
      }
    } catch (error) {
      console.error('Error processing approval:', error);
    } finally {
      setIsProcessingApproval(false);
    }
  };

  return (
    <div className="min-h-screen bg-void text-text flex flex-col">
      <header className="bg-surface border-b border-line p-4 shrink-0">
        <BackToPortfolio className="mb-2 inline-flex items-center gap-1.5 text-xs text-muted hover:text-accent transition-colors" />
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <h1 className="display text-2xl text-text">Agent Desk</h1>
            <p className="text-sm text-muted mt-1">
              Live multi-agent investment analysis — research, macro, quant, risk &amp; scribe
            </p>
          </div>
          {isRunning && (
            <span className="chip shrink-0 bg-accent/10 border-accent/30 text-accent">
              <Loader2 className="w-3 h-3 animate-spin mr-1.5 inline" />
              Running
            </span>
          )}
        </div>
      </header>

      <div className="shrink-0 bg-surface border-b border-line px-4 py-4">
        <div className="flex flex-col xl:flex-row gap-4 xl:items-end">
          <div className="flex-1 grid grid-cols-1 md:grid-cols-3 gap-3">
            <div>
              <label className="block text-[10px] uppercase tracking-wide text-muted mb-1.5">
                Ticker
              </label>
              <input
                type="text"
                value={ticker}
                onChange={(e) => setTicker(e.target.value.toUpperCase())}
                placeholder="e.g. NVDA"
                className="w-full bg-panel border border-line rounded-lg px-4 py-2.5 text-sm text-text placeholder:text-muted focus:outline-none focus:border-accent transition-colors"
                disabled={isRunning}
                maxLength={10}
              />
            </div>
            <div className="md:col-span-2">
              <label className="block text-[10px] uppercase tracking-wide text-muted mb-1.5">
                Analysis question
              </label>
              <input
                type="text"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="What would you like to analyze?"
                className="w-full bg-panel border border-line rounded-lg px-4 py-2.5 text-sm text-text placeholder:text-muted focus:outline-none focus:border-accent transition-colors"
                disabled={isRunning}
              />
            </div>
          </div>
          <button
            onClick={startAnalysis}
            disabled={isRunning || !ticker.trim()}
            className="btn btn-primary flex items-center gap-2 shrink-0"
          >
            {isRunning ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Running…
              </>
            ) : (
              <>
                <Play className="w-4 h-4" />
                Run Analysis
              </>
            )}
          </button>
        </div>

        <div className="flex flex-wrap gap-2 mt-3">
          {EXAMPLE_TICKERS.map((sym) => (
            <button
              key={sym}
              type="button"
              onClick={() => setTicker(sym)}
              disabled={isRunning}
              className={clsx(
                'chip transition-colors',
                ticker === sym
                  ? 'bg-accent/10 border-accent/40 text-accent'
                  : 'hover:border-muted hover:text-text'
              )}
            >
              <Zap className="w-3 h-3 inline mr-1 opacity-70" />
              {sym}
            </button>
          ))}
          <span className="text-[11px] text-muted self-center ml-1">
            Any public ticker — live agents + market data
          </span>
        </div>
      </div>

      <main className="flex-1 p-4 space-y-4">
        <motion.section
          className={clsx(
            'bg-surface border border-line rounded-lg overflow-hidden flex flex-col',
            graphTall ? 'h-[420px]' : 'h-[300px]'
          )}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <div className="px-4 py-3 border-b border-line flex items-center justify-between gap-2">
            <div className="flex items-center gap-2 min-w-0">
              <Network className="w-4 h-4 text-accent shrink-0" />
              <div className="min-w-0">
                <h2 className="display text-sm text-text leading-tight">Agent Network</h2>
                <p className="text-[11px] text-muted truncate">Orchestrator, analysts &amp; MCP tools</p>
              </div>
            </div>
            <button
              type="button"
              onClick={() => setGraphTall((v) => !v)}
              className={clsx('btn text-xs shrink-0', graphTall && 'bg-accent/10 border-accent/40 text-accent')}
            >
              {graphTall ? 'Compact' : 'Taller'}
            </button>
          </div>
          <AgentGraph
            events={events}
            activeAgents={activeAgents}
            className="flex-1 min-h-0"
            expanded={graphExpanded}
            onExpandChange={setGraphExpanded}
          />
        </motion.section>

        <motion.section
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05 }}
        >
          <RunOutputPanel
            events={events}
            memo={finalMemo || undefined}
            isMemoLoading={isRunning && activeAgents.has('scribe')}
            activeTab={activeTab}
            onTabChange={setActiveTab}
            ticker={ticker}
          />
        </motion.section>
      </main>

      <footer className="bg-surface border-t border-line px-4 py-2 shrink-0">
        <div className="flex items-center justify-between text-xs text-muted">
          <div className="flex items-center gap-4 font-mono">
            <span>Ticker: {ticker || '—'}</span>
            <span>Events: {events.length}</span>
            {tokenData?.total_tokens != null && (
              <span>Tokens: {tokenData.total_tokens.toLocaleString()}</span>
            )}
            {tokenData?.estimated_cost != null && (
              <span>Cost: ${tokenData.estimated_cost.toFixed(3)}</span>
            )}
          </div>
          <span>Agent Desk · Live</span>
        </div>
      </footer>

      <ApprovalDrawer
        isOpen={isApprovalOpen}
        onClose={() => setIsApprovalOpen(false)}
        approval={currentApproval || undefined}
        onApprove={handleApproval}
        isProcessing={isProcessingApproval}
      />
    </div>
  );
}
