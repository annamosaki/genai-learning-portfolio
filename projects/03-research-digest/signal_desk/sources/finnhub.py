"""Optional Finnhub free-tier market news (skipped when FINNHUB_API_KEY unset)."""

from __future__ import annotations

import hashlib
import os
from typing import Any, Callable

import httpx

FINNHUB_NEWS = "https://finnhub.io/api/v1/news"
USER_AGENT = "ResearchDigest/1.0 (annamosaki.com; personal reading desk)"


def _entry_id(url: str, headline: str) -> str:
    raw = url or headline
    return "fh-" + hashlib.sha1(raw.encode()).hexdigest()[:12]


async def fetch_finnhub(
    *,
    category: str = "general",
    max_results: int = 20,
    on_progress: Callable[[str, dict[str, Any]], Any] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    api_key = (os.getenv("FINNHUB_API_KEY") or "").strip()
    if not api_key:
        meta = {
            "ok": True,
            "skipped": True,
            "reason": "FINNHUB_API_KEY unset",
            "count": 0,
            "source": "finnhub",
        }
        if on_progress:
            await _maybe_await(
                on_progress("source.skipped", {"source": "finnhub", "reason": meta["reason"]})
            )
        return [], meta

    if on_progress:
        await _maybe_await(
            on_progress("source.fetching", {"source": "finnhub", "category": category})
        )

    try:
        async with httpx.AsyncClient(
            timeout=20.0,
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
        ) as client:
            resp = await client.get(
                FINNHUB_NEWS,
                params={"category": category, "token": api_key},
            )
            resp.raise_for_status()
            payload = resp.json()
    except Exception as exc:
        meta = {
            "ok": False,
            "skipped": True,
            "reason": str(exc)[:200],
            "count": 0,
            "source": "finnhub",
        }
        if on_progress:
            await _maybe_await(
                on_progress("source.skipped", {"source": "finnhub", "reason": meta["reason"]})
            )
        return [], meta

    if not isinstance(payload, list):
        payload = []

    items: list[dict[str, Any]] = []
    for row in payload[:max_results]:
        headline = (row.get("headline") or "").strip()
        url = (row.get("url") or "").strip()
        if not headline:
            continue
        summary = (row.get("summary") or "").strip()
        ts = row.get("datetime")
        date = None
        if isinstance(ts, (int, float)) and ts > 0:
            from datetime import datetime, timezone

            date = datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()
        items.append(
            {
                "id": _entry_id(url, headline),
                "kind": "news",
                "title": headline,
                "url": url,
                "text": summary[:900],
                "topics": [],
                "source": f"finnhub:{row.get('source') or 'news'}",
                "date": date,
            }
        )

    meta = {"ok": True, "skipped": False, "count": len(items), "source": "finnhub"}
    if on_progress:
        await _maybe_await(
            on_progress("source.fetched", {"source": "finnhub", "count": len(items)})
        )
    return items, meta


async def _maybe_await(result: Any) -> None:
    if hasattr(result, "__await__"):
        await result
