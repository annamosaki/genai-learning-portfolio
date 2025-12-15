"use client";

import { Fragment, type ReactNode, useState } from "react";
import Link from "next/link";
import { apiBase } from "@/lib/utils";

const SUGGESTIONS = [
  "What did Anna do at BNP Paribas?",
  "What are her strongest skills?",
  "Summarize her education.",
  "What awards has she won?",
];

type Msg = { role: "user" | "assistant"; content: string };

function renderInline(text: string): ReactNode[] {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**") && part.length > 4) {
      return (
        <strong key={i} className="font-semibold text-[var(--color-text)]">
          {part.slice(2, -2)}
        </strong>
      );
    }
    return <Fragment key={i}>{part}</Fragment>;
  });
}

function AssistantMessage({ content }: { content: string }) {
  const lines = content.replace(/\r\n/g, "\n").split("\n");
  const blocks: ReactNode[] = [];
  let listItems: string[] = [];

  const flushList = () => {
    if (!listItems.length) return;
    blocks.push(
      <ul key={`ul-${blocks.length}`} className="my-1.5 list-disc space-y-1.5 pl-5">
        {listItems.map((item, i) => (
          <li key={i} className="leading-relaxed">
            {renderInline(item)}
          </li>
        ))}
      </ul>,
    );
    listItems = [];
  };

  for (const raw of lines) {
    const bullet = raw.match(/^\s*(?:[-*]|\d+\.)\s+(.*)$/);
    if (bullet) {
      listItems.push(bullet[1]);
      continue;
    }
    flushList();
    if (raw.trim() === "") {
      blocks.push(<div key={`sp-${blocks.length}`} className="h-2" />);
      continue;
    }
    blocks.push(
      <p key={`p-${blocks.length}`} className="leading-relaxed">
        {renderInline(raw)}
      </p>,
    );
  }
  flushList();

  return <div className="space-y-0.5 text-sm">{blocks}</div>;
}

export default function AskPage() {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  async function send(q: string) {
    const question = q.trim();
    if (!question || loading) return;
    const history = messages.slice(-20);
    setInput("");
    setMessages((m) => [...m, { role: "user", content: question }]);
    setLoading(true);
    try {
      const res = await fetch(`${apiBase()}/api/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, history }),
      });
      if (!res.ok) throw new Error("fail");
      const data = await res.json();
      setMessages((m) => [...m, { role: "assistant", content: data.answer }]);
    } catch {
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          content:
            "API offline. Anna is an ENSAE-trained quant (BNP Paribas CIB) building ML for markets — NLP, forecasting, and multi-agent systems.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-16 sm:px-6">
      <Link
        href="/"
        className="mb-4 inline-flex items-center gap-1 text-sm text-[var(--color-muted)] hover:text-[var(--color-accent)]"
      >
        ← Back to home
      </Link>
      <p className="font-mono text-xs uppercase tracking-[0.18em] text-[var(--color-accent)]">
        CV chat
      </p>
      <h1 className="display mt-2 text-5xl">Ask Anna</h1>
      <p className="mt-3 text-[var(--color-muted)]">
        Her full CV is included in every reply, and this chat remembers the conversation.
      </p>

      <div className="mt-6 flex flex-wrap items-center gap-2">
        {SUGGESTIONS.map((s) => (
          <button key={s} type="button" onClick={() => send(s)} className="chip hover:text-[var(--color-accent)]">
            {s}
          </button>
        ))}
        {messages.length > 0 && (
          <button
            type="button"
            onClick={() => {
              if (loading) return;
              setMessages([]);
              setInput("");
            }}
            disabled={loading}
            className="chip text-[var(--color-muted)] hover:text-[var(--color-accent)] disabled:opacity-50"
          >
            Clear chat
          </button>
        )}
      </div>

      <div className="mt-8 min-h-[280px] space-y-3 rounded-2xl border border-[var(--color-line)] bg-[var(--color-panel)] p-4">
        {messages.length === 0 && (
          <p className="text-sm text-[var(--color-muted)]">No messages yet.</p>
        )}
        {messages.map((m, i) => (
          <div
            key={i}
            className={
              m.role === "user"
                ? "ml-8 rounded-xl bg-[var(--color-accent)]/15 px-3 py-2 text-sm"
                : "mr-8 rounded-xl border border-[var(--color-line)] px-3 py-2"
            }
          >
            {m.role === "assistant" ? <AssistantMessage content={m.content} /> : m.content}
          </div>
        ))}
        {loading && <p className="font-mono text-xs text-[var(--color-muted)]">Thinking…</p>}
      </div>

      <form
        className="mt-4 flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about experience, skills, education…"
          className="flex-1 rounded-full border border-[var(--color-line)] bg-[var(--color-void)] px-4 py-2 text-sm outline-none focus:border-[var(--color-accent)]"
        />
        <button type="submit" disabled={loading} className="btn btn-primary">
          Send
        </button>
      </form>
    </div>
  );
}
