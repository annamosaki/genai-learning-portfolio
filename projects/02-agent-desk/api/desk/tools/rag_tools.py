"""RAG search over the local SEC filings index (NVDA/AAPL/MSFT cache)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np

from ..llm import llm_client
from ..rag.bm25 import BM25
from ..rag.hybrid import HybridRetriever
from ..rag.store import data_store


def _chunk_text(chunk: Dict[str, Any]) -> str:
    return chunk.get("text") or chunk.get("content") or ""


def _chunk_source(chunk: Dict[str, Any]) -> str:
    return chunk.get("source") or chunk.get("source_file") or "Unknown"


async def search_filings(
    query: str,
    ticker: Optional[str] = None,
    top_k: int = 5,
) -> dict[str, Any]:
    """
    Hybrid BM25 + dense search with correct chunk field names.
    Optionally filter to a ticker's source documents.
    """
    chunks = data_store.load_chunks()
    embeddings = data_store.load_embeddings()
    bm25_data = data_store.load_bm25_index()

    if not chunks:
        return {
            "ok": False,
            "results": [],
            "error": "No indexed filings available",
            "tool_used": "search_filings",
            "service": "rag",
            "retrieval_mode": "unavailable",
            "transport": "local_hybrid_rag",
            "_transport": "local_hybrid_rag",
        }

    # Build index of eligible chunk indices (ticker filter)
    eligible: Optional[List[int]] = None
    if ticker:
        ticker_u = ticker.upper()
        eligible = [
            i
            for i, c in enumerate(chunks)
            if ticker_u in _chunk_source(c).upper()
            or ticker_u in _chunk_text(c)[:200].upper()
        ]
        if not eligible:
            return {
                "ok": True,
                "results": [],
                "message": f"No local index hits for {ticker_u}; use Edgar for live filings",
                "tool_used": "search_filings",
                "service": "rag",
                "retrieval_mode": "empty_ticker_filter",
                "transport": "local_hybrid_rag",
                "_transport": "local_hybrid_rag",
                "query": query,
                "ticker": ticker_u,
            }

    try:
        search_results: List[Dict[str, Any]] = []
        retrieval_mode = "none"
        trace_fields: Dict[str, Any] = {}

        if embeddings is not None and llm_client.has_api_key():
            query_embedding = await llm_client.embed_single(query)

            if bm25_data:
                bm25_index = BM25.from_dict(bm25_data)
                hybrid = HybridRetriever(bm25_index, embeddings)
                ranked, trace = await hybrid.search(
                    query, query_embedding, top_k=max(top_k * 4, 20)
                )
                retrieval_mode = "hybrid_bm25_dense"
                if isinstance(trace, dict):
                    trace_fields = {
                        "bm25_hits": trace.get("bm25_results_count"),
                        "dense_hits": trace.get("dense_results_count"),
                        "fusion_method": trace.get("fusion_method") or "rrf",
                    }
                for chunk_idx, score, _ranks in ranked:
                    if eligible is not None and chunk_idx not in eligible:
                        continue
                    if chunk_idx >= len(chunks):
                        continue
                    chunk = chunks[chunk_idx]
                    search_results.append(
                        {
                            "content": _chunk_text(chunk)[:2000],
                            "source": _chunk_source(chunk),
                            "relevance_score": float(score),
                            "chunk_id": chunk.get("id", str(chunk_idx)),
                        }
                    )
                    if len(search_results) >= top_k:
                        break
            else:
                # Dense-only
                retrieval_mode = "dense_only"
                sims = []
                for i, emb in enumerate(embeddings):
                    if eligible is not None and i not in eligible:
                        continue
                    denom = (np.linalg.norm(query_embedding) * np.linalg.norm(emb))
                    sim = float(np.dot(query_embedding, emb) / denom) if denom else 0.0
                    sims.append((i, sim))
                sims.sort(key=lambda x: x[1], reverse=True)
                for chunk_idx, score in sims[:top_k]:
                    chunk = chunks[chunk_idx]
                    search_results.append(
                        {
                            "content": _chunk_text(chunk)[:2000],
                            "source": _chunk_source(chunk),
                            "relevance_score": float(score),
                            "chunk_id": chunk.get("id", str(chunk_idx)),
                        }
                    )
        else:
            # BM25-only or keyword fallback (no API key / no embeddings)
            if bm25_data:
                retrieval_mode = "bm25_only"
                bm25_index = BM25.from_dict(bm25_data)
                hits = bm25_index.search(query, top_k=max(top_k * 4, 20))
                for chunk_idx, score in hits:
                    if eligible is not None and chunk_idx not in eligible:
                        continue
                    chunk = chunks[chunk_idx]
                    search_results.append(
                        {
                            "content": _chunk_text(chunk)[:2000],
                            "source": _chunk_source(chunk),
                            "relevance_score": float(score),
                            "chunk_id": chunk.get("id", str(chunk_idx)),
                        }
                    )
                    if len(search_results) >= top_k:
                        break
            else:
                retrieval_mode = "keyword_fallback"
                q = query.lower()
                for i, chunk in enumerate(chunks):
                    if eligible is not None and i not in eligible:
                        continue
                    text = _chunk_text(chunk)
                    if any(tok in text.lower() for tok in q.split()[:6]):
                        search_results.append(
                            {
                                "content": text[:2000],
                                "source": _chunk_source(chunk),
                                "relevance_score": 0.5,
                                "chunk_id": chunk.get("id", str(i)),
                            }
                        )
                    if len(search_results) >= top_k:
                        break

        return {
            "ok": True,
            "results": search_results,
            "tool_used": "search_filings",
            "service": "rag",
            "retrieval_mode": retrieval_mode,
            "transport": "local_hybrid_rag",
            "_transport": "local_hybrid_rag",
            "query": query,
            "ticker": ticker,
            "results_count": len(search_results),
            **trace_fields,
        }
    except Exception as e:
        return {
            "ok": False,
            "results": [],
            "error": f"Search error: {e}",
            "tool_used": "search_filings",
            "service": "rag",
            "retrieval_mode": "error",
            "transport": "local_hybrid_rag",
            "_transport": "local_hybrid_rag",
        }
