'use client';

import { useState, useEffect } from 'react';
import { clsx } from 'clsx';
import { motion } from 'framer-motion';
import type { Level } from '@/lib/types';
import { LEVEL_META } from '@/lib/constants';
import { apiUrl } from '@/lib/api';

interface LadderRailProps {
  selectedLevel: string;
  onLevelSelect: (levelId: string) => void;
}

export function LadderRail({ selectedLevel, onLevelSelect }: LadderRailProps) {
  const [levels, setLevels] = useState<Level[]>(LEVEL_META);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Try to fetch levels from API, fallback to hardcoded
    fetch(apiUrl('/api/levels'))
      .then(res => res.json())
      .then(data => {
        if (Array.isArray(data)) {
          setLevels(data);
        } else if (Array.isArray(data?.levels)) {
          setLevels(data.levels);
        }
      })
      .catch(() => {
        // Use fallback data
        console.log('Using fallback level data');
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="w-80 bg-surface border-r border-line flex flex-col h-full">
        <div className="rail-header animate-pulse">
          <div className="h-5 w-40 bg-panel rounded mb-2" />
          <div className="h-3 w-56 bg-panel rounded" />
        </div>
        <div className="flex-1 overflow-y-auto p-4">
          {Array.from({ length: 12 }).map((_, i) => (
            <div key={i} className="h-16 bg-panel rounded mb-2 animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="w-80 bg-surface border-r border-line flex flex-col h-full min-h-0">
      <div className="rail-header">
        <h2 className="display text-lg text-text leading-tight">Foundation Ladder</h2>
        <p className="text-sm text-muted mt-0.5 leading-tight">
          Explore {levels.length} levels of LLM capabilities
        </p>
      </div>

      <div className="flex-1 overflow-y-auto min-h-0 p-4 space-y-2">
        {levels.map((level, index) => (
          <motion.button
            key={level.id}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.05 }}
            onClick={() => onLevelSelect(level.id)}
            className={clsx(
              'w-full text-left p-4 rounded-lg border transition-all duration-200',
              'hover:bg-panel hover:border-muted',
              selectedLevel === level.id
                ? 'bg-accent/10 border-accent text-accent'
                : 'bg-surface border-line text-text'
            )}
          >
            <div className="flex items-start gap-3">
              <div
                className={clsx(
                  'flex-shrink-0 w-8 h-8 rounded-full border-2 flex items-center justify-center text-sm font-mono font-medium',
                  selectedLevel === level.id
                    ? 'border-accent bg-accent text-void'
                    : 'border-line bg-panel text-muted'
                )}
              >
                {level.number}
              </div>
              <div className="min-w-0 flex-1">
                <div className="font-medium text-sm mb-1">{level.title}</div>
                <div
                  className={clsx(
                    'text-xs leading-relaxed',
                    selectedLevel === level.id ? 'text-accent/80' : 'text-muted'
                  )}
                >
                  {level.blurb}
                </div>
              </div>
            </div>
          </motion.button>
        ))}
      </div>

      <div className="shrink-0 p-4 border-t border-line">
        <div className="text-xs text-muted text-center">
          Select a level to explore its capabilities
        </div>
      </div>
    </div>
  );
}