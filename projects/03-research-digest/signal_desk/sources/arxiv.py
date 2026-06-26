"""ArXiv Atom API fetcher (free, no API key).

Respects ArXiv's courtesy rate limit (~1 request / 3s).
"""

from __future__ import annotations

import asyncio
import hashlib
import re
from typing import Any, Callable
from urllib.parse import quote_plus

import httpx

ARXIV_API = "https://export.arxiv.org/api/query"
USER_AGENT = "ResearchDigest/1.0 (annamosaki.com; personal reading desk)"
# ArXiv asks for ≥3s between requests from the same client
REQUEST_GAP_SEC = 3.2


def _entry_id(url: str) -> str:
    return "arxiv-" + hashlib.sha1(url.encode()).hexdigest()[:12]


def _abs_url(entry_id: str) -> str:
    m = re.search(r"(\d{4}\.\d{4,5})(v\d+)?$", entry_id)
    if m:
        return f"https://arxiv.org/abs/{m.group(1)}"
    return entry_id.replace("http://", "https://")


def _parse_atom(xml: str) -> list[dict[str, Any]]:
    try:
        import feedparser
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("feedparser is required for ArXiv fetching") from exc

    feed = feedparser.parse(xml)
    items: list[dict[str, Any]] = []
    for e in feed.entries:
        title = re.sub(r"\s+", " ", (e.get("title") or "").strip())
        summary = re.sub(r"\s+", " ", (e.get("summary") or e.get("description") or "").strip())
        link = e.get("id") or e.get("link") or ""
        url = _abs_url(str(link))
        authors = ", ".join(a.get("name", "") for a in (e.get("authors") or []) if a.get("name"))
        published = (e.get("published") or e.get("updated") or "")[:10]
        items.append(
            {
                "id": _entry_id(url),
                "kind": "literature",
                "title": title,
                "authors": authors,
                "venue": "arXiv",
                "url": url,
                "abstract": summary[:1200],
                "topics": [],
                "source": "arxiv",
                "date": published or None,
                "year": int(published[:4]) if published[:4].isdigit() else None,
            }
        )
    return items


async def fetch_arxiv(
    queries: list[str],
    *,
    max_results: int = 25,
    on_progress: Callable[[str, dict[str, Any]], Any] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Fetch papers for each query; dedupe by abs URL. Returns (items, meta)."""
    if not queries:
        return [], {"ok": False, "reason": "no queries", "count": 0}

    per_query = max(8, max_results // max(len(queries), 1))
    seen: set[str] = set()
    items: list[dict[str, Any]] = []
    errors: list[str] = []

    async with httpx.AsyncClient(
        timeout=45.0,
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
    ) as client:
        for i, q in enumerate(queries):
            if i > 0:
                await asyncio.sleep(REQUEST_GAP_SEC)
            if on_progress:
                await _maybe_await(on_progress("source.fetching", {"source": "arxiv", "query": q}))
            url = (
                f"{ARXIV_API}?search_query={quote_plus(q)}"
                f"&start=0&max_results={per_query}"
                f"&sortBy=submittedDate&sortOrder=descending"
            )
            try:
                resp = await client.get(url)
                if resp.status_code == 429:
                    # Back off once and retry
                    await asyncio.sleep(REQUEST_GAP_SEC * 2)
                    resp = await client.get(url)
                if resp.status_code == 429:
                    errors.append(f"rate limited: {q[:60]}")
                    continue
                resp.raise_for_status()
                if "Rate exceeded" in resp.text:
                    errors.append(f"rate exceeded: {q[:60]}")
                    continue
                batch = _parse_atom(resp.text)
                for row in batch:
                    if row["url"] in seen:
                        continue
                    seen.add(row["url"])
                    items.append(row)
            except Exception as exc:
                errors.append(f"{q[:60]}: {exc}")

    meta = {
        "ok": len(items) > 0 or not errors,
        "count": len(items),
        "errors": errors,
        "source": "arxiv",
    }
    if on_progress:
        etype = "source.fetched" if items else "source.skipped"
        await _maybe_await(
            on_progress(
                etype,
                {"source": "arxiv", "count": len(items), "errors": errors[:3]},
            )
        )
    return items[:max_results], meta


async def _maybe_await(result: Any) -> None:
    if hasattr(result, "__await__"):
        await result
