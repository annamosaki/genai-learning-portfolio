"""Corpus document management + lightweight reindex."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from .config import settings
from .retrieval.bm25 import BM25
from .retrieval.chunking import chunk_document
from .retrieval.store import data_store


def _corpus_dir() -> Path:
    p = Path(settings.corpus_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _index_dir() -> Path:
    p = Path(settings.index_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _safe_name(filename: str) -> str:
    name = Path(filename).name
    name = re.sub(r"[^\w.\-]+", "_", name)
    if not name.lower().endswith((".md", ".txt")):
        name = f"{name}.md"
    return name


def list_documents() -> List[Dict[str, Any]]:
    chunks = data_store.load_chunks() or []
    counts: Dict[str, int] = {}
    for c in chunks:
        src = c.get("source") or "unknown"
        counts[src] = counts.get(src, 0) + 1

    docs: List[Dict[str, Any]] = []
    for path in sorted(_corpus_dir().glob("*")):
        if path.suffix.lower() not in {".md", ".txt"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        docs.append(
            {
                "id": path.name,
                "name": path.name,
                "path": str(path),
                "bytes": path.stat().st_size,
                "chars": len(text),
                "chunk_count": counts.get(path.name, 0),
                "preview": text[:280].replace("\n", " "),
                "uploaded": path.name.startswith("upload_"),
            }
        )
    return docs


def get_document(doc_id: str) -> Optional[Dict[str, Any]]:
    path = _corpus_dir() / Path(doc_id).name
    if not path.exists() or path.suffix.lower() not in {".md", ".txt"}:
        return None
    text = path.read_text(encoding="utf-8", errors="replace")
    chunks = [c for c in (data_store.load_chunks() or []) if c.get("source") == path.name]
    return {
        "id": path.name,
        "name": path.name,
        "bytes": path.stat().st_size,
        "chars": len(text),
        "chunk_count": len(chunks),
        "content": text,
        "chunks": [
            {
                "id": c.get("id"),
                "heading": c.get("heading"),
                "text": c.get("text", "")[:500],
                "method": c.get("method"),
                "size": c.get("size"),
            }
            for c in chunks[:40]
        ],
        "uploaded": path.name.startswith("upload_"),
    }


def save_document(filename: str, content: str) -> Dict[str, Any]:
    safe = _safe_name(filename)
    if not safe.startswith("upload_"):
        safe = f"upload_{safe}"
    path = _corpus_dir() / safe
    path.write_text(content, encoding="utf-8")
    return {"id": safe, "name": safe, "bytes": path.stat().st_size, "chars": len(content)}


def delete_document(doc_id: str) -> bool:
    path = _corpus_dir() / Path(doc_id).name
    if not path.exists():
        return False
    # Only allow deleting user uploads (protect seed filings)
    if not path.name.startswith("upload_"):
        raise PermissionError("Seed corpus filings cannot be deleted from the demo UI")
    path.unlink()
    return True


def _hash_embed(text: str, dim: int) -> np.ndarray:
    """Deterministic pseudo-embedding when no OpenAI key (demo-only)."""
    seed = abs(hash(text)) % (2**32)
    rng = np.random.default_rng(seed)
    vec = rng.standard_normal(dim).astype(np.float32)
    norm = np.linalg.norm(vec)
    return vec / norm if norm else vec


async def reindex_corpus(use_openai_embeddings: bool = True) -> Dict[str, Any]:
    """Rebuild chunks + BM25 (+ embeddings) from all corpus files."""
    started = time.time()
    corpus_files = sorted(
        [p for p in _corpus_dir().glob("*") if p.suffix.lower() in {".md", ".txt"}]
    )
    if not corpus_files:
        raise RuntimeError("No corpus documents found")

    all_chunks: List[Dict[str, Any]] = []
    for path in corpus_files:
        text = path.read_text(encoding="utf-8", errors="replace")
        file_chunks = chunk_document(
            text,
            source=path.name,
            method="smart",
            chunk_size=800,
            overlap=100,
        )
        all_chunks.extend(file_chunks)

    index_dir = _index_dir()
    chunks_path = index_dir / "chunks.json"
    with open(chunks_path, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, indent=2)

    # BM25
    texts = [c["text"] for c in all_chunks]
    bm25 = BM25()
    bm25.fit(texts)
    with open(index_dir / "bm25.json", "w", encoding="utf-8") as f:
        json.dump(bm25.to_dict(), f)

    emb_path = index_dir / "embeddings.npy"
    dim = 1536
    if emb_path.exists():
        try:
            old = np.load(emb_path)
            if old.ndim == 2 and old.shape[1] > 0:
                dim = int(old.shape[1])
        except Exception:
            pass

    embeddings: Optional[np.ndarray] = None
    embed_mode = "hash"

    if use_openai_embeddings and settings.openai_api_key:
        try:
            from .retrieval.embed import EmbeddingManager

            manager = EmbeddingManager()
            embeddings = await manager.create_embeddings(all_chunks)
            embed_mode = "openai"
        except Exception as exc:
            print(f"Embedding via OpenAI failed, falling back to hash: {exc}")

    if embeddings is None:
        embeddings = np.vstack([_hash_embed(c["text"], dim) for c in all_chunks]).astype(np.float32)
        embed_mode = "hash"

    np.save(emb_path, embeddings)
    data_store.clear_cache()

    return {
        "documents": len(corpus_files),
        "chunks": len(all_chunks),
        "embeddings_shape": list(embeddings.shape),
        "embed_mode": embed_mode,
        "elapsed_seconds": round(time.time() - started, 2),
    }
