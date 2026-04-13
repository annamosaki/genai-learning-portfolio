'use client';

import { useState, useRef, useEffect } from 'react';
import { clsx } from 'clsx';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, Trash2, RotateCcw, Zap } from 'lucide-react';
import type { Message, ChatResponse, SecurityTier } from '@/lib/types';
import { SAMPLE_SUGGESTIONS, SECURITY_TIERS } from '@/lib/constants';
import { apiUrl } from '@/lib/api';

interface ChatPaneProps {
  selectedLevel: string;
  onResponse: (response: ChatResponse) => void;
  compareMode: boolean;
  compareLevel?: string;
}

export function ChatPane({ selectedLevel, onResponse, compareMode, compareLevel }: ChatPaneProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [selectedSecurity, setSelectedSecurity] = useState('none');
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const isSecuredLevel = selectedLevel === 'secured';

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim(),
      timestamp: Date.now(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);
    setError(null);

    try {
      const opts = {
        ...(isSecuredLevel ? { security_tier: selectedSecurity } : {}),
      };
      const history = messages.map(m => ({ role: m.role, content: m.content }));

      let answer = "No answer returned.";
      let result: any = {};

      if (compareMode && compareLevel) {
        const response = await fetch(apiUrl('/api/compare'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            levels: [selectedLevel, compareLevel],
            question: userMessage.content,
            history,
            opts,
          }),
        });
        if (!response.ok) {
          const errorData = await response.json().catch(() => ({ error: 'Request failed' }));
          throw new Error(errorData.detail || errorData.error || `Request failed with status ${response.status}`);
        }
        const data = await response.json();
        const results = data.results || {};
        const a = results[selectedLevel];
        const b = results[compareLevel];
        answer = [
          `### ${selectedLevel}\n${a?.answer ?? '(no answer)'}`,
          `### ${compareLevel}\n${b?.answer ?? '(no answer)'}`,
        ].join('\n\n');
        result = { answer, trace: a?.trace, citations: a?.citations, level: selectedLevel, compare: results };
      } else {
        const response = await fetch(apiUrl('/api/chat'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            level: selectedLevel,
            question: userMessage.content,
            history,
            opts,
          }),
        });
        if (!response.ok) {
          const errorData = await response.json().catch(() => ({ error: 'Request failed' }));
          throw new Error(errorData.detail || errorData.error || `Request failed with status ${response.status}`);
        }
        const data = await response.json();
        result = data.result ?? data;
        answer = result.answer ?? "No answer returned.";
      }

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: answer,
        timestamp: Date.now(),
      };

      setMessages(prev => [...prev, assistantMessage]);
      onResponse({
        answer,
        trace: result.trace,
        citations: result.citations,
        level: result.level,
      } as ChatResponse);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Something went wrong';
      setError(errorMessage);
      
      // Add error message to chat
      const errorChatMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `Error: ${errorMessage}. Please try again or check your connection.`,
        timestamp: Date.now(),
      };
      setMessages(prev => [...prev, errorChatMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const clearChat = () => {
    setMessages([]);
    setError(null);
  };

  const useSuggestion = (suggestion: string) => {
    setInput(suggestion);
    textareaRef.current?.focus();
  };

  const retryLastMessage = () => {
    if (messages.length >= 2) {
      const lastUserMessage = messages[messages.length - 2];
      if (lastUserMessage.role === 'user') {
        setInput(lastUserMessage.content);
        setMessages(prev => prev.slice(0, -2)); // Remove last user and assistant messages
        textareaRef.current?.focus();
      }
    }
  };

  return (
    <div className="flex-1 flex flex-col bg-void min-h-0 h-full">
      {/* Header — matches Ladder / Inspector rail-header height */}
      <div className="rail-header">
        <div className="flex items-center justify-between gap-3">
          <div className="min-w-0">
            <h2 className="display text-lg text-text leading-tight">
              {compareMode && compareLevel ? 'Compare Mode' : 'Chat'}
            </h2>
            <p className="text-sm text-muted mt-0.5 leading-tight truncate">
              {compareMode && compareLevel
                ? `Comparing ${selectedLevel} vs ${compareLevel}`
                : `Level: ${selectedLevel}`}
            </p>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {isSecuredLevel && (
              <select
                value={selectedSecurity}
                onChange={(e) => setSelectedSecurity(e.target.value)}
                className="btn text-sm"
              >
                {SECURITY_TIERS.map(tier => (
                  <option key={tier.id} value={tier.id}>
                    {tier.name}
                  </option>
                ))}
              </select>
            )}
            {error && (
              <button
                onClick={retryLastMessage}
                className="btn text-sm"
                title="Retry last message"
              >
                <RotateCcw className="w-4 h-4" />
              </button>
            )}
            <button
              onClick={clearChat}
              className="btn text-sm"
              disabled={messages.length === 0}
              title="Clear chat"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto min-h-0 p-4 space-y-4">
        <AnimatePresence>
          {messages.map((message) => (
            <motion.div
              key={message.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className={clsx(
                'flex gap-3',
                message.role === 'user' ? 'justify-end' : 'justify-start'
              )}
            >
              <div
                className={clsx(
                  'max-w-[80%] p-4 rounded-lg',
                  message.role === 'user'
                    ? 'bg-accent text-void'
                    : message.content.startsWith('Error:')
                    ? 'bg-red-500/10 border border-red-500/20 text-red-400'
                    : 'bg-surface border border-line text-text'
                )}
              >
                <div className="whitespace-pre-wrap text-sm leading-relaxed">
                  {message.content}
                </div>
                <div className="text-xs opacity-60 mt-2">
                  {new Date(message.timestamp).toLocaleTimeString()}
                </div>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>

        {loading && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex justify-start"
          >
            <div className="bg-surface border border-line p-4 rounded-lg">
              <div className="flex items-center gap-2 text-sm text-muted">
                <div className="flex space-x-1">
                  <div className="w-2 h-2 bg-accent rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-accent rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                  <div className="w-2 h-2 bg-accent rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                </div>
                Thinking...
              </div>
            </div>
          </motion.div>
        )}

        {/* Suggestions */}
        {messages.length === 0 && !loading && (
          <div className="space-y-4">
            <div className="text-center text-muted">
              <h3 className="font-medium mb-2">Try asking something like:</h3>
            </div>
            <div className="grid gap-2">
              {SAMPLE_SUGGESTIONS.map((suggestion, index) => (
                <motion.button
                  key={index}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.1 }}
                  onClick={() => useSuggestion(suggestion)}
                  className="text-left p-3 bg-surface border border-line rounded-lg hover:bg-panel hover:border-muted transition-colors text-sm text-muted hover:text-text"
                >
                  <Zap className="w-4 h-4 inline mr-2 text-accent" />
                  {suggestion}
                </motion.button>
              ))}
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="shrink-0 p-4 border-t border-line bg-surface">
        <div className="flex gap-3">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder={`Ask about ${selectedLevel} level...`}
            className="flex-1 bg-panel border border-line rounded-lg px-4 py-3 text-text placeholder-muted resize-none focus:outline-none focus:border-accent transition-colors"
            rows={1}
            style={{
              minHeight: '44px',
              maxHeight: '120px',
            }}
            onInput={(e) => {
              const target = e.target as HTMLTextAreaElement;
              target.style.height = '44px';
              target.style.height = `${Math.min(target.scrollHeight, 120)}px`;
            }}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || loading}
            className="btn-primary px-4"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}