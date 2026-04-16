'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { clsx } from 'clsx';
import {
  FileText,
  Upload,
  Trash2,
  RefreshCw,
  ChevronLeft,
  Loader2,
} from 'lucide-react';
import { apiUrl } from '@/lib/api';
import type { CorpusDocument, CorpusDocumentDetail } from '@/lib/types';

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

export function CorpusBrowser() {
  const [docs, setDocs] = useState<CorpusDocument[]>([]);
  const [selected, setSelected] = useState<CorpusDocumentDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const loadList = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(apiUrl('/api/documents'));
      if (!res.ok) throw new Error(`Failed to list documents (${res.status})`);
      const data = await res.json();
      setDocs(data.documents || []);
    } catch (e: any) {
      setError(e.message || 'Failed to load corpus');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadList();
  }, [loadList]);

  const openDoc = async (id: string) => {
    setBusy(true);
    setError(null);
    try {
      const res = await fetch(apiUrl(`/api/documents/${encodeURIComponent(id)}`));
      if (!res.ok) throw new Error(`Failed to load document (${res.status})`);
      const data = await res.json();
      setSelected(data);
    } catch (e: any) {
      setError(e.message || 'Failed to open document');
    } finally {
      setBusy(false);
    }
  };

  const upload = async (file: File) => {
    setBusy(true);
    setError(null);
    setStatus('Uploading & reindexing…');
    try {
      const form = new FormData();
      form.append('file', file);
      form.append('reindex', 'true');
      const res = await fetch(apiUrl('/api/documents'), {
        method: 'POST',
        body: form,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Upload failed (${res.status})`);
      }
      const data = await res.json();
      const ri = data.reindex;
      setStatus(
        ri
          ? `Indexed ${ri.chunks} chunks from ${ri.documents} docs (${ri.embed_mode}, ${ri.elapsed_seconds}s)`
          : 'Uploaded'
      );
      await loadList();
      if (data.document?.id) await openDoc(data.document.id);
    } catch (e: any) {
      setError(e.message || 'Upload failed');
      setStatus(null);
    } finally {
      setBusy(false);
    }
  };

  const remove = async (id: string) => {
    if (!confirm(`Delete ${id}? Index will be rebuilt.`)) return;
    setBusy(true);
    setError(null);
    try {
      const res = await fetch(
        apiUrl(`/api/documents/${encodeURIComponent(id)}?reindex=true`),
        { method: 'DELETE' }
      );
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Delete failed (${res.status})`);
      }
      setSelected(null);
      setStatus(`Deleted ${id}`);
      await loadList();
    } catch (e: any) {
      setError(e.message || 'Delete failed');
    } finally {
      setBusy(false);
    }
  };

  const reindex = async () => {
    setBusy(true);
    setError(null);
    setStatus('Reindexing corpus…');
    try {
      const res = await fetch(apiUrl('/api/documents/reindex'), { method: 'POST' });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Reindex failed (${res.status})`);
      }
      const data = await res.json();
      setStatus(
        `Rebuilt ${data.chunks} chunks · ${data.embed_mode} · ${data.elapsed_seconds}s`
      );
      await loadList();
      if (selected) await openDoc(selected.id);
    } catch (e: any) {
      setError(e.message || 'Reindex failed');
      setStatus(null);
    } finally {
      setBusy(false);
    }
  };

  if (selected) {
    return (
      <div className="flex flex-col h-full min-h-0">
        <div className="shrink-0 px-4 py-3 border-b border-line flex items-center gap-2">
          <button
            type="button"
            onClick={() => setSelected(null)}
            className="btn text-xs flex items-center gap-1"
          >
            <ChevronLeft className="w-3.5 h-3.5" />
            Corpus
          </button>
          <div className="min-w-0 flex-1">
            <div className="text-sm font-medium text-text truncate">{selected.name}</div>
            <div className="text-xs text-muted">
              {formatBytes(selected.bytes)} · {selected.chunk_count} chunks
              {selected.uploaded ? ' · upload' : ' · seed'}
            </div>
          </div>
          {selected.uploaded && (
            <button
              type="button"
              disabled={busy}
              onClick={() => remove(selected.id)}
              className="btn text-xs text-red-400 border-red-500/30"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        <div className="flex-1 overflow-y-auto min-h-0 p-4 space-y-4">
          <div>
            <h4 className="text-xs uppercase tracking-wide text-muted mb-2">Full text</h4>
            <pre className="text-xs text-muted whitespace-pre-wrap font-mono bg-panel border border-line rounded-lg p-3 max-h-72 overflow-y-auto">
              {selected.content}
            </pre>
          </div>
          {selected.chunks?.length > 0 && (
            <div>
              <h4 className="text-xs uppercase tracking-wide text-muted mb-2">
                Indexed chunks ({selected.chunks.length}
                {selected.chunk_count > selected.chunks.length ? '+' : ''})
              </h4>
              <div className="space-y-2">
                {selected.chunks.map((c, i) => (
                  <div key={c.id || i} className="bg-panel border border-line rounded-lg p-3">
                    <div className="flex items-center gap-2 mb-1 text-xs text-muted">
                      {c.heading && <span className="chip">{c.heading}</span>}
                      {c.method && <span>{c.method}</span>}
                      {c.size != null && <span>{c.size} chars</span>}
                    </div>
                    <pre className="text-xs text-muted whitespace-pre-wrap font-mono">
                      {c.text}
                    </pre>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full min-h-0">
      <div className="shrink-0 px-4 py-3 border-b border-line space-y-2">
        <p className="text-xs text-muted leading-relaxed">
          Documents used by RAG levels. Upload <code className="text-accent">.md</code> /{' '}
          <code className="text-accent">.txt</code> to expand the corpus; reindex rebuilds
          chunks &amp; embeddings.
        </p>
        <div className="flex flex-wrap gap-2">
          <input
            ref={fileRef}
            type="file"
            accept=".md,.txt,text/markdown,text/plain"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) upload(f);
              e.target.value = '';
            }}
          />
          <button
            type="button"
            disabled={busy}
            onClick={() => fileRef.current?.click()}
            className="btn text-xs flex items-center gap-1.5 bg-accent/15 border-accent/40 text-accent"
          >
            {busy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Upload className="w-3.5 h-3.5" />}
            Upload
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={reindex}
            className="btn text-xs flex items-center gap-1.5"
          >
            <RefreshCw className={clsx('w-3.5 h-3.5', busy && 'animate-spin')} />
            Reindex
          </button>
        </div>
        {status && <p className="text-xs text-accent">{status}</p>}
        {error && <p className="text-xs text-red-400">{error}</p>}
      </div>

      <div className="flex-1 overflow-y-auto min-h-0 p-3">
        {loading ? (
          <div className="text-center text-muted py-10 text-sm flex items-center justify-center gap-2">
            <Loader2 className="w-4 h-4 animate-spin" /> Loading corpus…
          </div>
        ) : docs.length === 0 ? (
          <div className="text-center text-muted py-10 text-sm">No documents in corpus</div>
        ) : (
          <div className="space-y-2">
            {docs.map((doc) => (
              <button
                key={doc.id}
                type="button"
                onClick={() => openDoc(doc.id)}
                className="w-full text-left bg-panel border border-line rounded-lg p-3 hover:border-accent/40 transition-colors"
              >
                <div className="flex items-start gap-2">
                  <FileText className="w-4 h-4 text-accent mt-0.5 shrink-0" />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-medium text-text truncate">{doc.name}</span>
                      {doc.uploaded && <span className="chip text-xs">upload</span>}
                    </div>
                    <div className="text-xs text-muted mt-0.5">
                      {formatBytes(doc.bytes)} · {doc.chunk_count} chunks
                    </div>
                    <p className="text-xs text-muted mt-1 line-clamp-2">{doc.preview}</p>
                  </div>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
