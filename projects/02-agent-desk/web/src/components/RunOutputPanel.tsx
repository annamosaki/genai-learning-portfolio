'use client';

import { clsx } from 'clsx';
import { Activity, FileText, ListOrdered } from 'lucide-react';
import EventTimeline from '@/components/EventTimeline';
import MemoPanel from '@/components/MemoPanel';

interface Event {
  type: string;
  timestamp: string;
  agent?: string;
  data: Record<string, unknown>;
}

interface RunOutputPanelProps {
  events: Event[];
  memo?: string;
  isMemoLoading: boolean;
  activeTab: 'timeline' | 'memo';
  onTabChange: (tab: 'timeline' | 'memo') => void;
  ticker?: string;
}

export function RunOutputPanel({
  events,
  memo,
  isMemoLoading,
  activeTab,
  onTabChange,
  ticker,
}: RunOutputPanelProps) {
  const tabs = [
    { key: 'timeline' as const, label: 'Event Timeline', icon: ListOrdered, count: events.length },
    { key: 'memo' as const, label: 'Investment Memo', icon: FileText, count: memo ? 1 : 0 },
  ];

  return (
    <div className="bg-surface border border-line rounded-lg flex flex-col">
      <div className="shrink-0 border-b border-line">
        <div className="flex overflow-x-auto">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const hasData =
              tab.key === 'timeline' ? events.length > 0 : !!memo || isMemoLoading;

            return (
              <button
                key={tab.key}
                type="button"
                onClick={() => onTabChange(tab.key)}
                className={clsx(
                  'flex items-center gap-1.5 px-4 py-3 text-xs font-medium border-b-2 transition-colors whitespace-nowrap',
                  activeTab === tab.key
                    ? 'border-accent text-accent bg-accent/5'
                    : hasData
                      ? 'border-transparent text-text hover:text-accent'
                      : 'border-transparent text-muted hover:text-text'
                )}
              >
                <Icon className="w-3.5 h-3.5" />
                {tab.label}
                {tab.count > 0 && <span className="chip text-[10px]">{tab.count}</span>}
              </button>
            );
          })}
        </div>
      </div>

      <div>
        {activeTab === 'timeline' ? (
          events.length === 0 ? (
            <div className="flex flex-col items-center justify-center text-muted p-12">
              <Activity className="w-10 h-10 mb-3 opacity-40" />
              <p className="text-sm">Run an analysis to stream agent events here.</p>
              <p className="text-xs mt-1 opacity-70">Try any ticker — e.g. NVDA, AAPL, or TSLA.</p>
            </div>
          ) : (
            <EventTimeline events={events} embedded />
          )
        ) : (
          <MemoPanel memo={memo} isLoading={isMemoLoading} embedded ticker={ticker} />
        )}
      </div>
    </div>
  );
}
