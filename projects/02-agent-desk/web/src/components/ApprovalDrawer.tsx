'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { Check, Edit, FileText, Loader2, X, XCircle } from 'lucide-react';
import { useEffect, useState } from 'react';

interface ApprovalGate {
  gate_id: string;
  type: string;
  description: string;
  content: string;
}

interface ApprovalDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  approval?: ApprovalGate;
  onApprove: (decision: 'approve' | 'edit' | 'deny', message?: string) => void;
  isProcessing: boolean;
}

export default function ApprovalDrawer({
  isOpen,
  onClose,
  approval,
  onApprove,
  isProcessing,
}: ApprovalDrawerProps) {
  const [message, setMessage] = useState('');
  const [editError, setEditError] = useState('');
  const [selectedDecision, setSelectedDecision] = useState<'approve' | 'edit' | 'deny' | null>(
    null
  );

  // Reset local UI state whenever a new gate opens (plan → memo reuse)
  useEffect(() => {
    if (!approval?.gate_id) return;
    setMessage('');
    setEditError('');
    setSelectedDecision(null);
  }, [approval?.gate_id]);

  useEffect(() => {
    if (!isOpen) {
      setSelectedDecision(null);
      setEditError('');
    }
  }, [isOpen]);

  const handleDecision = (decision: 'approve' | 'edit' | 'deny') => {
    if (isProcessing) return;
    if (decision === 'edit' && !message.trim()) {
      setEditError('Describe what to change before submitting Edit.');
      return;
    }
    setEditError('');
    setSelectedDecision(decision);
    onApprove(decision, message.trim() || undefined);
  };

  if (!approval) return null;

  const busy = isProcessing;
  const approveLabel =
    busy && selectedDecision === 'approve'
      ? 'Approving…'
      : busy && selectedDecision === 'edit'
        ? 'Submitting…'
        : busy && selectedDecision === 'deny'
          ? 'Denying…'
          : 'Approve';

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            className="fixed inset-0 bg-black/60 z-40"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={busy ? undefined : onClose}
          />

          <motion.div
            className="fixed right-0 top-0 h-full w-full max-w-md bg-surface border-l border-line z-50 flex flex-col shadow-2xl"
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'tween', duration: 0.25 }}
          >
            <div className="rail-header flex-row items-center justify-between !h-auto !py-4">
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-accent" />
                <div>
                  <h3 className="display text-base text-text">Approval Required</h3>
                  <p className="text-xs text-muted capitalize">{approval.type} gate</p>
                </div>
              </div>
              <button type="button" onClick={onClose} className="btn p-2" disabled={busy}>
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              <p className="text-sm text-muted">{approval.description}</p>

              <div>
                <h4 className="text-[10px] uppercase tracking-wide text-muted mb-2">Preview</h4>
                <pre className="text-[11px] leading-relaxed text-muted font-mono bg-panel border border-line rounded-lg p-3 max-h-64 overflow-y-auto whitespace-pre-wrap">
                  {approval.content}
                </pre>
              </div>

              <div>
                <label className="block text-[10px] uppercase tracking-wide text-muted mb-1.5">
                  Feedback <span className="text-muted/70">(required for Edit)</span>
                </label>
                <textarea
                  value={message}
                  onChange={(e) => {
                    setMessage(e.target.value);
                    if (editError) setEditError('');
                  }}
                  placeholder="e.g. Drop macro, focus on RSI — or expand the valuation section…"
                  className="w-full bg-panel border border-line rounded-lg px-4 py-3 text-sm text-text placeholder:text-muted focus:outline-none focus:border-accent resize-none"
                  rows={3}
                  disabled={busy}
                />
                {editError ? (
                  <p className="mt-1.5 text-xs text-red-400">{editError}</p>
                ) : (
                  <p className="mt-1.5 text-[11px] text-muted">
                    Edit re-plans agents (plan gate) or selectively re-runs specialists + scribe
                    (memo gate).
                  </p>
                )}
              </div>
            </div>

            <div className="p-4 border-t border-line space-y-2 bg-surface">
              <button
                type="button"
                onClick={() => handleDecision('approve')}
                disabled={busy}
                className="w-full btn btn-primary gap-2"
              >
                {busy && selectedDecision === 'approve' ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Check className="w-4 h-4" />
                )}
                {approveLabel}
              </button>

              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => handleDecision('edit')}
                  disabled={busy || !message.trim()}
                  className="flex-1 btn gap-2"
                  title={
                    message.trim()
                      ? 'Revise with your feedback'
                      : 'Add feedback above to enable Edit'
                  }
                >
                  <Edit className="w-4 h-4" />
                  {busy && selectedDecision === 'edit' ? 'Submitting…' : 'Edit'}
                </button>
                <button
                  type="button"
                  onClick={() => handleDecision('deny')}
                  disabled={busy}
                  className="flex-1 btn gap-2 border-red-500/30 text-red-400 hover:border-red-400/50"
                >
                  <XCircle className="w-4 h-4" />
                  {busy && selectedDecision === 'deny' ? 'Denying…' : 'Deny'}
                </button>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
