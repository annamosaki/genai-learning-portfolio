'use client';

import { useState } from 'react';
import { clsx } from 'clsx';
import { motion } from 'framer-motion';
import { GitCompare, BarChart3 } from 'lucide-react';
import { LadderRail } from '@/components/LadderRail';
import { ChatPane } from '@/components/ChatPane';
import { Inspector } from '@/components/Inspector';
import { EvalBoard } from '@/components/EvalBoard';
import { BackToPortfolio } from '@/components/BackToPortfolio';
import type { ChatResponse } from '@/lib/types';

export function HomeClient() {
  const [selectedLevel, setSelectedLevel] = useState('stateless');
  const [lastResponse, setLastResponse] = useState<ChatResponse | null>(null);
  const [compareMode, setCompareMode] = useState(false);
  const [compareLevel, setCompareLevel] = useState<string>('');
  const [showEvals, setShowEvals] = useState(false);

  const handleLevelSelect = (levelId: string) => {
    if (compareMode && compareLevel === '') {
      setCompareLevel(levelId);
      return;
    }

    if (levelId !== selectedLevel) {
      setLastResponse(null);
    }
    setSelectedLevel(levelId);
    if (compareMode && compareLevel === levelId) {
      setCompareLevel('');
    }
  };

  const toggleCompareMode = () => {
    setCompareMode(!compareMode);
    if (!compareMode) {
      setCompareLevel('');
    }
  };

  const toggleEvals = () => {
    setShowEvals(!showEvals);
  };

  return (
    <div className="h-screen bg-void text-text flex flex-col">
      <header className="bg-surface border-b border-line p-4">
        <div className="flex items-center justify-between gap-4">
          <div className="min-w-0">
            <BackToPortfolio className="mb-2 inline-flex items-center gap-1.5 text-xs text-muted hover:text-accent transition-colors" />
            <h1 className="display text-2xl text-text">LLM Foundation Ladder</h1>
            <p className="text-sm text-muted mt-1">
              Explore 12 progressive levels of LLM capabilities and techniques
            </p>
          </div>
          <div className="flex items-center gap-3 shrink-0">
            <button
              onClick={toggleEvals}
              className={clsx(
                'btn flex items-center gap-2',
                showEvals && 'bg-accent text-void border-accent'
              )}
            >
              <BarChart3 className="w-4 h-4" />
              Evaluations
            </button>
            <button
              onClick={toggleCompareMode}
              className={clsx(
                'btn flex items-center gap-2',
                compareMode && 'bg-accent text-void border-accent'
              )}
            >
              <GitCompare className="w-4 h-4" />
              Compare
            </button>
          </div>
        </div>

        {compareMode && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            className="mt-3 p-3 bg-accent/10 border border-accent/20 rounded-lg"
          >
            <div className="text-sm text-accent">
              Compare Mode Active:
              <span className="font-medium ml-1">
                {selectedLevel}
                {compareLevel ? ` vs ${compareLevel}` : ' (select second level)'}
              </span>
            </div>
          </motion.div>
        )}
      </header>

      <div className="flex-1 flex overflow-hidden min-h-0">
        <LadderRail
          selectedLevel={compareMode ? (compareLevel || selectedLevel) : selectedLevel}
          onLevelSelect={handleLevelSelect}
        />

        <div className="flex-1 flex flex-col min-h-0 min-w-0">
          {showEvals ? (
            <div className="flex-1 overflow-y-auto p-6">
              <EvalBoard selectedLevel={selectedLevel} />
            </div>
          ) : (
            <ChatPane
              key={selectedLevel}
              selectedLevel={selectedLevel}
              onResponse={setLastResponse}
              compareMode={compareMode}
              compareLevel={compareLevel}
            />
          )}
        </div>

        {!showEvals && (
          <Inspector lastResponse={lastResponse} selectedLevel={selectedLevel} />
        )}
      </div>

      <footer className="bg-surface border-t border-line px-4 py-2">
        <div className="flex items-center justify-between text-xs text-muted">
          <div className="flex items-center gap-4">
            <span>Level: {selectedLevel}</span>
            {lastResponse?.trace?.usage && (
              <span>
                Tokens:{' '}
                {(lastResponse.trace.usage.prompt_tokens ??
                  lastResponse.trace.usage.input_tokens ??
                  '?') +
                  ' / ' +
                  (lastResponse.trace.usage.completion_tokens ??
                    lastResponse.trace.usage.output_tokens ??
                    '?')}
              </span>
            )}
            {typeof lastResponse?.trace?.elapsed_seconds === 'number' && (
              <span>Latency: {Math.round(lastResponse.trace.elapsed_seconds * 1000)}ms</span>
            )}
            {lastResponse?.trace?.cost?.totalCost != null && (
              <span>Cost: ${lastResponse.trace.cost.totalCost.toFixed(4)}</span>
            )}
          </div>
          <div>LLM Foundation Ladder Demo</div>
        </div>
      </footer>
    </div>
  );
}
