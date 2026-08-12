"""Curated RSS / Atom fetcher for fund research and news (free)."""

from __future__ import annotations

import hashlib
import re
from typing import Any, Callable

import httpx

USER_AGENT = "ResearchDigest/1.0 (annamosaki.com; personal reading desk)"


def _entry_id(url: str, title: str) -> str:
    raw = url or title
    return "rss-" + hashlib.sha1(raw.encode()).hexdigest()[:12]


def _clean(text: str, limit: int = 800) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


async def fetch_rss(
    feeds: list[dict[str, Any]],
    *,
    on_progress: Callable[[str, dict[str, Any]], Any] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Fetch multiple RSS/Atom feeds. Each feed dict: name, url, kind, max_results."""
    if not feeds:
        return [], {"ok": True, "count": 0, "source": "rss", "feeds": []}

    try:
        import feedparser
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("feedparser is required for RSS fetching") from exc

    items: list[dict[str, Any]] = []
    feed_meta: list[dict[str, Any]] = []
    seen: set[str] = set()

    async with httpx.AsyncClient(
        timeout=25.0,
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
    ) as client:
        for feed in feeds:
            name = feed.get("name") or "rss"
            url = feed.get("url") or ""
            kind = feed.get("kind") or "fund_research"
            limit = int(feed.get("max_results") or 8)
            if not url:
                feed_meta.append({"name": name, "ok": False, "reason": "missing url", "count": 0})
                continue

            if on_progress:
                await _maybe_await(
                    on_progress("source.fetching", {"source": "rss", "feed": name, "url": url})
                )

            try:
                resp = await client.get(url)
                resp.raise_for_status()
                ctype = (resp.headers.get("content-type") or "").lower()
                parsed = feedparser.parse(resp.text)
                if not parsed.entries:
                    reason = "empty or not a feed"
                    if "html" in ctype and "xml" not in ctype and "atom" not in ctype and "rss" not in ctype:
                        reason = "HTML response (feed URL likely dead)"
                    feed_meta.append({"name": name, "ok": False, "reason": reason, "count": 0})
                    if on_progress:
                        await _maybe_await(
                            on_progress(
                                "source.skipped",
                                {"source": "rss", "feed": name, "reason": reason},
                            )
                        )
                    continue
                count = 0
                for e in parsed.entries[:limit]:
                    title = _clean(e.get("title") or "", 240)
                    link = e.get("link") or e.get("id") or ""
                    if not title:
                        continue
                    key = link or title
                    if key in seen:
                        continue
                    seen.add(key)
                    raw_summary = e.get("summary") or e.get("description") or ""
                    if not raw_summary and isinstance(e.get("content"), list) and e.get("content"):
                        raw_summary = e["content"][0].get("value", "")
                    summary = _clean(raw_summary, 900)
                    published = (e.get("published") or e.get("updated") or "")[:10]
                    items.append(
                        {
                            "id": _entry_id(str(link), title),
                            "kind": kind,
                            "title": title,
                            "url": str(link) if link else "",
                            "text": summary,
                            "abstract": summary,
                            "topics": [],
                            "source": name,
                            "date": published or None,
                            "venue": name,
                        }
                    )
                    count += 1
                feed_meta.append({"name": name, "ok": True, "count": count})
                if on_progress:
                    await _maybe_await(
                        on_progress(
                            "source.fetched",
                            {"source": "rss", "feed": name, "count": count},
                        )
                    )
            except Exception as exc:
                feed_meta.append({"name": name, "ok": False, "reason": str(exc), "count": 0})
                if on_progress:
                    await _maybe_await(
                        on_progress(
                            "source.skipped",
                            {"source": "rss", "feed": name, "reason": str(exc)[:200]},
                        )
                    )

    ok_any = any(f.get("ok") for f in feed_meta) or not feed_meta
    return items, {
        "ok": ok_any,
        "count": len(items),
        "source": "rss",
        "feeds": feed_meta,
    }


async def _maybe_await(result: Any) -> None:
    if hasattr(result, "__await__"):
        await result
