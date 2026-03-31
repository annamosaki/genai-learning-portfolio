"""Helpers for rich, inspector-friendly traces."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def serialize_chunk(
    chunk: Dict[str, Any],
    *,
    score: Optional[float] = None,
    rank: Optional[int] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    item: Dict[str, Any] = {
        "id": chunk.get("id"),
        "text": (chunk.get("text") or "")[:2500],
        "source": chunk.get("source"),
        "heading": chunk.get("heading"),
        "method": chunk.get("method"),
        "size": chunk.get("size") or len(chunk.get("text") or ""),
    }
    if score is not None:
        item["score"] = float(score)
    if rank is not None:
        item["rank"] = rank
    if extra:
        item.update(extra)
    return item


def append_step(
    steps: List[Dict[str, Any]],
    *,
    action: str,
    detail: Optional[Dict[str, Any]] = None,
    elapsed_seconds: Optional[float] = None,
    status: str = "ok",
) -> None:
    steps.append(
        {
            "step": len(steps) + 1,
            "action": action,
            "status": status,
            "elapsed_seconds": elapsed_seconds,
            "detail": detail or {},
        }
    )
