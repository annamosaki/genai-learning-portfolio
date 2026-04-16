'use client';

import { useState, useEffect } from 'react';
import { clsx } from 'clsx';
import { motion } from 'framer-motion';
import { RefreshCw, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import type { EvalResult } from '@/lib/types';
import { apiUrl } from '@/lib/api';

interface EvalBoardProps {
  selectedLevel: string;
}

export function EvalBoard({ selectedLevel }: EvalBoardProps) {
  const [evals, setEvals] = useState<EvalResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchEvals = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(apiUrl('/api/evals'));
      
      if (!response.ok) {
        throw new Error('Failed to fetch evaluations');
      }

      const data = await response.json();
      // Backend returns { overall_summary, level_results, ... } or a list
      let rows: EvalResult[] = [];
      if (Array.isArray(data)) {
        rows = data;
      } else if (data?.level_results && typeof data.level_results === 'object') {
        rows = Object.entries(data.level_results).flatMap(([level, payload]: [string, any]) => {
          const results = payload?.results || payload?.questions || [];
          if (Array.isArray(results)) {
            return results.map((r: any, i: number) => ({
              id: `${level}-${i}`,
              level,
              question: r.question || r.question_id || '',
              expectedAnswer: r.expected_answer || '',
              actualAnswer: r.answer || r.actual_answer || '',
              score: r.overall_score ?? r.score ?? payload?.average_score ?? 0,
              metrics: {
                accuracy: r.metrics?.faithfulness ?? r.metrics?.accuracy ?? 0,
                relevance: r.metrics?.answer_relevance ?? r.metrics?.relevance ?? 0,
                completeness: r.metrics?.citation_rate ?? r.metrics?.completeness ?? 0,
              },
              timestamp: Date.now(),
            }));
          }
          return [{
            id: level,
            level,
            question: 'Aggregate',
            expectedAnswer: '',
            actualAnswer: '',
            score: payload?.average_score ?? 0,
            metrics: { accuracy: 0, relevance: 0, completeness: 0 },
            timestamp: Date.now(),
          }];
        });
      }
      if (selectedLevel) {
        rows = rows.filter((r) => r.level === selectedLevel || selectedLevel === 'all');
      }
      setEvals(rows);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load evaluations');
      setEvals([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEvals();
  }, [selectedLevel]);

  const averageScore = evals.length > 0 
    ? evals.reduce((sum, evalResult) => sum + evalResult.score, 0) / evals.length 
    : 0;

  const averageMetrics = evals.length > 0 
    ? {
        accuracy: evals.reduce((sum, evalResult) => sum + evalResult.metrics.accuracy, 0) / evals.length,
        relevance: evals.reduce((sum, evalResult) => sum + evalResult.metrics.relevance, 0) / evals.length,
        completeness: evals.reduce((sum, evalResult) => sum + evalResult.metrics.completeness, 0) / evals.length,
      }
    : { accuracy: 0, relevance: 0, completeness: 0 };

  const getScoreColor = (score: number) => {
    if (score >= 0.8) return 'text-accent';
    if (score >= 0.6) return 'text-accent-2';
    if (score >= 0.4) return 'text-yellow-400';
    return 'text-red-400';
  };

  const getScoreTrend = (score: number) => {
    if (score >= 0.8) return <TrendingUp className="w-4 h-4 text-accent" />;
    if (score >= 0.6) return <Minus className="w-4 h-4 text-accent-2" />;
    return <TrendingDown className="w-4 h-4 text-red-400" />;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="display text-lg text-text">Evaluation Board</h3>
          <p className="text-sm text-muted">
            Performance metrics for {selectedLevel} level
          </p>
        </div>
        <button
          onClick={fetchEvals}
          disabled={loading}
          className="btn"
        >
          <RefreshCw className={clsx('w-4 h-4', loading && 'animate-spin')} />
        </button>
      </div>

      {/* Summary Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-panel border border-line rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm text-muted">Overall Score</div>
              <div className={clsx('text-2xl font-mono font-medium', getScoreColor(averageScore))}>
                {(averageScore * 100).toFixed(1)}%
              </div>
            </div>
            {getScoreTrend(averageScore)}
          </div>
        </div>

        <div className="bg-panel border border-line rounded-lg p-4">
          <div className="text-sm text-muted">Accuracy</div>
          <div className={clsx('text-2xl font-mono font-medium', getScoreColor(averageMetrics.accuracy))}>
            {(averageMetrics.accuracy * 100).toFixed(1)}%
          </div>
        </div>

        <div className="bg-panel border border-line rounded-lg p-4">
          <div className="text-sm text-muted">Relevance</div>
          <div className={clsx('text-2xl font-mono font-medium', getScoreColor(averageMetrics.relevance))}>
            {(averageMetrics.relevance * 100).toFixed(1)}%
          </div>
        </div>

        <div className="bg-panel border border-line rounded-lg p-4">
          <div className="text-sm text-muted">Completeness</div>
          <div className={clsx('text-2xl font-mono font-medium', getScoreColor(averageMetrics.completeness))}>
            {(averageMetrics.completeness * 100).toFixed(1)}%
          </div>
        </div>
      </div>

      {/* Error State */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4">
          <div className="text-red-400 text-sm">
            {error}
          </div>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="animate-pulse">
              <div className="h-20 bg-panel rounded-lg"></div>
            </div>
          ))}
        </div>
      )}

      {/* Evaluation Results */}
      {!loading && !error && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="font-medium text-text">Recent Evaluations</h4>
            <div className="chip">
              {evals.length} results
            </div>
          </div>

          {evals.length > 0 ? (
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {evals
                .sort((a, b) => b.timestamp - a.timestamp)
                .map((evalResult, index) => (
                  <motion.div
                    key={evalResult.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.05 }}
                    className="bg-panel border border-line rounded-lg p-4"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium text-text truncate">
                          {evalResult.question}
                        </div>
                        <div className="text-xs text-muted mt-1">
                          {new Date(evalResult.timestamp).toLocaleString()}
                        </div>
                      </div>
                      <div className={clsx('chip ml-3', getScoreColor(evalResult.score))}>
                        {(evalResult.score * 100).toFixed(0)}%
                      </div>
                    </div>

                    <div className="grid grid-cols-3 gap-3 text-xs">
                      <div>
                        <div className="text-muted">Accuracy</div>
                        <div className={clsx('font-mono', getScoreColor(evalResult.metrics.accuracy))}>
                          {(evalResult.metrics.accuracy * 100).toFixed(0)}%
                        </div>
                      </div>
                      <div>
                        <div className="text-muted">Relevance</div>
                        <div className={clsx('font-mono', getScoreColor(evalResult.metrics.relevance))}>
                          {(evalResult.metrics.relevance * 100).toFixed(0)}%
                        </div>
                      </div>
                      <div>
                        <div className="text-muted">Complete</div>
                        <div className={clsx('font-mono', getScoreColor(evalResult.metrics.completeness))}>
                          {(evalResult.metrics.completeness * 100).toFixed(0)}%
                        </div>
                      </div>
                    </div>

                    <details className="mt-3">
                      <summary className="text-xs text-muted cursor-pointer hover:text-text">
                        View details
                      </summary>
                      <div className="mt-2 pt-2 border-t border-line space-y-2 text-xs">
                        <div>
                          <div className="text-muted font-medium">Expected:</div>
                          <div className="text-text bg-surface p-2 rounded mt-1">
                            {evalResult.expectedAnswer}
                          </div>
                        </div>
                        <div>
                          <div className="text-muted font-medium">Actual:</div>
                          <div className="text-text bg-surface p-2 rounded mt-1">
                            {evalResult.actualAnswer}
                          </div>
                        </div>
                      </div>
                    </details>
                  </motion.div>
                ))}
            </div>
          ) : (
            <div className="text-center text-muted py-8">
              <div className="w-16 h-16 bg-panel rounded-full mx-auto mb-4 flex items-center justify-center">
                <TrendingUp className="w-8 h-8 text-muted" />
              </div>
              <p>No evaluations available for this level</p>
              <p className="text-sm mt-1">Run some queries to see performance metrics</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}