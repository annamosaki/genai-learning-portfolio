"""Personalized literature, news & fund-research digest pipeline.

Free sources: ArXiv + curated RSS (+ optional Finnhub). Local JSONL as seed/fallback.
No email. No Resend.
"""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Awaitable, Callable

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None

from .sources.arxiv import fetch_arxiv
from .sources.finnhub import fetch_finnhub
from .sources.local import fetch_local_inbox, fetch_local_jsonl
from .sources.rss import fetch_rss

_FOCUS_STOP = {
    "a",
    "an",
    "and",
    "or",
    "the",
    "of",
    "in",
    "on",
    "for",
    "to",
    "with",
    "about",
    "into",
    "over",
    "vs",
    "versus",
    "using",
    "based",
    "from",
    "that",
    "this",
    "these",
    "those",
    "my",
    "our",
    "me",
    "i",
}

PROJECT = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[3]
TOPICS_PATH = PROJECT / "topics.yaml"
OUT = ROOT / "content" / "artifacts" / "signal-desk" / "latest-review.json"
OUT_LEGACY = ROOT / "content" / "artifacts" / "signal-desk" / "latest-issue.json"
PUBLIC_COPY = ROOT / "apps" / "web" / "public" / "artifacts" / "signal-desk"

# Lambda / container layout: flatten paths via env
import os

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env", override=False)
except Exception:
    pass

if os.environ.get("SERVERLESS") == "1" or os.environ.get("LAMBDA_TASK_ROOT"):
    task = Path(os.environ.get("LAMBDA_TASK_ROOT") or Path(__file__).resolve().parents[1])
    PROJECT = task
    ROOT = task
    TOPICS_PATH = task / "topics.yaml"
    art = Path(os.environ.get("ARTIFACT_DIR") or "/tmp/artifacts/signal-desk")
    art.mkdir(parents=True, exist_ok=True)
    OUT = art / "latest-review.json"
    OUT_LEGACY = art / "latest-issue.json"
    PUBLIC_COPY = art  # best-effort local copy only

ProgressCb = Callable[[str, dict[str, Any]], Awaitable[None] | None]

# Prefer these topics when scoring (plan: TS-finance + quant dominate)
_BOOST_TOPICS = {"time-series", "quant-research", "user-focus"}


@dataclass
class State:
    topics_cfg: dict[str, Any] = field(default_factory=dict)
    items: list[dict[str, Any]] = field(default_factory=list)
    ranked: list[dict[str, Any]] = field(default_factory=list)
    draft_sections: list[dict[str, Any]] = field(default_factory=list)
    verified_sections: list[dict[str, Any]] = field(default_factory=list)
    claims_dropped: int = 0
    matched_topics: list[str] = field(default_factory=list)
    source_stats: dict[str, Any] = field(default_factory=dict)
    live_sources_used: bool = False
    focus_query: str = ""
    focus_keywords: list[str] = field(default_factory=list)


def load_topics(path: Path = TOPICS_PATH) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    if yaml is not None:
        return yaml.safe_load(raw) or {}
    return {
        "profile": "Anna Mosaki",
        "topics": [
            {"id": "time-series", "label": "Time series × finance", "weight": 1.0, "keywords": ["volatility", "forecasting"]},
            {"id": "quant-research", "label": "Quantitative research", "weight": 1.0, "keywords": ["alpha", "risk"]},
        ],
        "rules": {"drop_unsupported_claims": True, "max_items_per_section": 6},
        "sources": {},
    }


def parse_focus_keywords(focus: str) -> list[str]:
    """Turn free-text focus into ranking / ArXiv keywords."""
    text = (focus or "").strip()
    if not text:
        return []
    parts = [p.strip() for p in re.split(r"[,;\n|/]+", text) if p.strip()]
    keywords: list[str] = []
    seen: set[str] = set()

    def add(term: str) -> None:
        cleaned = re.sub(r"\s+", " ", term).strip(" .")
        if len(cleaned) < 2:
            return
        key = cleaned.lower()
        if key in seen or key in _FOCUS_STOP:
            return
        seen.add(key)
        keywords.append(cleaned)

    if len(parts) >= 2:
        for p in parts:
            add(p)
    else:
        # Keep the full phrase, then useful tokens.
        add(text)
        for token in re.findall(r"[A-Za-z][A-Za-z0-9\-+]{2,}", text):
            add(token)
    return keywords[:24]


def _arxiv_query_from_focus(keywords: list[str]) -> str | None:
    if not keywords:
        return None
    terms = keywords[:5]
    clauses = [f'all:"{t}"' for t in terms]
    return " OR ".join(clauses)


def apply_focus_to_topics(cfg: dict[str, Any], focus: str) -> tuple[dict[str, Any], list[str]]:
    """Inject a high-weight user-focus topic; optionally override lede."""
    keywords = parse_focus_keywords(focus)
    if not keywords:
        return cfg, []
    topics = list(cfg.get("topics") or [])
    topics = [t for t in topics if t.get("id") != "user-focus"]
    topics.insert(
        0,
        {
            "id": "user-focus",
            "label": "Your focus",
            "weight": 1.55,
            "keywords": keywords,
        },
    )
    cfg = {**cfg, "topics": topics, "focus": focus.strip()}
    return cfg, keywords


def _dedupe(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for item in items:
        key = (item.get("url") or "").strip() or f"{item.get('kind')}:{item.get('title')}"
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


async def ingest_async(
    state: State,
    *,
    live: bool = True,
    on_progress: ProgressCb | None = None,
    focus_query: str = "",
) -> State:
    cfg = load_topics()
    cfg, focus_keywords = apply_focus_to_topics(cfg, focus_query)
    state.topics_cfg = cfg
    state.focus_query = (focus_query or "").strip()
    state.focus_keywords = focus_keywords
    sources = state.topics_cfg.get("sources") or {}
    items: list[dict[str, Any]] = []
    stats: dict[str, Any] = {}

    # --- Literature: ArXiv + local ---
    lit_cfgs = sources.get("literature") or []
    arxiv_queries: list[str] = []
    arxiv_max = 25
    for cfg_src in lit_cfgs:
        stype = cfg_src.get("type")
        if stype == "arxiv" and live:
            arxiv_queries.extend(cfg_src.get("queries") or [])
            arxiv_max = int(cfg_src.get("max_results") or 25)
        elif stype == "local_jsonl":
            path = PROJECT / cfg_src["path"]
            rows = fetch_local_jsonl(path, default_kind="literature")
            items.extend(rows)
            stats["local_literature"] = {"ok": True, "count": len(rows)}
        elif stype == "local_inbox":
            path = PROJECT / cfg_src["path"]
            rows = fetch_local_inbox(path, cfg_src.get("kind") or "literature")
            items.extend(rows)
            stats["papers_inbox"] = {"ok": True, "count": len(rows)}

    focus_arxiv = _arxiv_query_from_focus(focus_keywords)
    if live and focus_arxiv:
        # Put user focus first so ArXiv rate budget prefers it.
        arxiv_queries = [focus_arxiv, *[q for q in arxiv_queries if q != focus_arxiv]][:3]
        stats["focus"] = {"query": state.focus_query, "keywords": focus_keywords, "arxiv_query": focus_arxiv}

    if live and arxiv_queries:
        arxiv_items, arxiv_meta = await fetch_arxiv(
            arxiv_queries, max_results=arxiv_max, on_progress=on_progress
        )
        items.extend(arxiv_items)
        stats["arxiv"] = arxiv_meta
        if arxiv_meta.get("count", 0) > 0:
            state.live_sources_used = True
    elif live:
        stats["arxiv"] = {"ok": True, "skipped": True, "reason": "no queries", "count": 0}

    # --- Fund research RSS ---
    fund_feeds = [f for f in (sources.get("fund_research") or []) if f.get("type") == "rss"]
    if live and fund_feeds:
        rss_items, rss_meta = await fetch_rss(fund_feeds, on_progress=on_progress)
        items.extend(rss_items)
        stats["rss"] = rss_meta
        if rss_meta.get("count", 0) > 0:
            state.live_sources_used = True
    else:
        stats["rss"] = {"ok": True, "skipped": not live, "count": 0}

    # --- News: Finnhub + local ---
    news_cfgs = sources.get("news") or []
    for cfg_src in news_cfgs:
        stype = cfg_src.get("type")
        if stype == "finnhub" and live:
            fh_items, fh_meta = await fetch_finnhub(
                category=cfg_src.get("category") or "general",
                max_results=int(cfg_src.get("max_results") or 20),
                on_progress=on_progress,
            )
            items.extend(fh_items)
            stats["finnhub"] = fh_meta
            if fh_meta.get("count", 0) > 0:
                state.live_sources_used = True
        elif stype == "local_jsonl":
            path = PROJECT / cfg_src["path"]
            rows = fetch_local_jsonl(path, default_kind="news")
            items.extend(rows)
            stats["local_news"] = {"ok": True, "count": len(rows)}
        elif stype == "local_inbox":
            path = PROJECT / cfg_src["path"]
            rows = fetch_local_inbox(path, cfg_src.get("kind") or "news")
            items.extend(rows)
            stats["news_inbox"] = {"ok": True, "count": len(rows)}

    if "finnhub" not in stats:
        stats["finnhub"] = {"ok": True, "skipped": True, "reason": "not configured", "count": 0}

    # Offline fallback: if live fetched nothing literature-like, local seed already merged.
    state.items = _dedupe(items)
    state.source_stats = stats
    return state


def ingest(state: State) -> State:
    """Sync wrapper: local-only ingest (used by older callers / tests)."""
    return asyncio.run(ingest_async(state, live=False))


def _score_item(
    item: dict[str, Any],
    topics: list[dict[str, Any]],
    *,
    focus_keywords: list[str] | None = None,
) -> tuple[float, list[str]]:
    blob = " ".join(
        str(item.get(k, ""))
        for k in ("title", "abstract", "text", "venue", "authors", "source")
    ).lower()
    explicit = set(item.get("topics") or [])
    score = 0.0
    matched: list[str] = []
    for t in topics:
        tid = t["id"]
        weight = float(t.get("weight", 1.0))
        hit = tid in explicit
        kw_hits = 0
        for kw in t.get("keywords") or []:
            if kw.lower() in blob:
                hit = True
                kw_hits += 1
        if hit:
            boost = 1.15 if tid in _BOOST_TOPICS else 1.0
            # Extra weight for the user-focus topic
            if tid == "user-focus":
                boost *= 1.25 + 0.08 * min(kw_hits, 5)
            score += weight * boost * (1.0 + 0.05 * min(kw_hits, 4))
            matched.append(tid)
    if item.get("unsupported"):
        score *= 0.05
    # Slight preference for live primary sources
    src = str(item.get("source") or "")
    if src == "arxiv":
        score *= 1.08

    # When the user set a focus field, demote items that miss it so ranking is field-specific.
    if focus_keywords:
        focus_hits = sum(1 for kw in focus_keywords if kw.lower() in blob)
        if focus_hits == 0:
            score *= 0.18
        else:
            score *= 1.0 + 0.12 * min(focus_hits, 4)
            if "user-focus" not in matched:
                matched.append("user-focus")
    return score, matched


def personalize_and_rank(state: State) -> State:
    topics = state.topics_cfg.get("topics") or []
    ranked = []
    topic_hits: set[str] = set()
    for item in state.items:
        score, matched = _score_item(item, topics, focus_keywords=state.focus_keywords)
        if score <= 0:
            continue
        topic_hits.update(matched)
        ranked.append({**item, "score": round(score, 3), "matched_topics": matched})
    ranked.sort(key=lambda x: (-x["score"], x.get("title", "")))
    state.ranked = ranked
    state.matched_topics = sorted(topic_hits)
    return state


def _para_from_item(item: dict[str, Any], cite_id: str) -> dict[str, Any]:
    body = item.get("abstract") or item.get("text") or ""
    snippet = body[:220].rstrip()
    if len(body) > 220:
        snippet += "…"
    text = f"{item['title']} — {snippet}" if snippet else item["title"]
    return {
        "text": text,
        "citations": [{"id": cite_id, "url": item.get("url", ""), "title": item["title"]}],
        "supported": not item.get("unsupported", False),
        "meta": {
            "score": item.get("score"),
            "topics": item.get("matched_topics", []),
            "kind": item.get("kind"),
            "source": item.get("source"),
            "date": item.get("date"),
            "authors": item.get("authors"),
        },
    }


def synthesize(state: State) -> State:
    rules = state.topics_cfg.get("rules") or {}
    limit = int(rules.get("max_items_per_section", 6))

    lit = [i for i in state.ranked if i.get("kind") == "literature"][:limit]
    news = [i for i in state.ranked if i.get("kind") == "news"][:limit]
    fund = [i for i in state.ranked if i.get("kind") == "fund_research"][:limit]

    lit_paras = [_para_from_item(item, str(i)) for i, item in enumerate(lit, 1)]
    news_paras = [_para_from_item(item, f"n{i}") for i, item in enumerate(news, 1)]
    fund_paras = [_para_from_item(item, f"f{i}") for i, item in enumerate(fund, 1)]

    watch_bits = []
    if state.focus_query:
        watch_bits.append(f"Focus this run: {state.focus_query}.")
    watch_bits.append(
        f"Matched topics: {', '.join(state.matched_topics) or 'none matched'}."
    )
    watch = [
        {
            "text": " ".join(watch_bits),
            "citations": [],
            "supported": True,
            "meta": {"kind": "watchlist", "focus": state.focus_query or None},
        }
    ]

    state.draft_sections = [
        {"heading": "Literature", "paragraphs": lit_paras},
        {"heading": "News", "paragraphs": news_paras},
        {"heading": "Fund research", "paragraphs": fund_paras},
        {"heading": "Watchlist", "paragraphs": watch},
    ]
    return state


def verify(state: State) -> State:
    drop = bool((state.topics_cfg.get("rules") or {}).get("drop_unsupported_claims", True))
    verified = []
    dropped = 0
    for section in state.draft_sections:
        paras = []
        for p in section["paragraphs"]:
            if drop and not p.get("supported", True):
                dropped += 1
                continue
            paras.append(
                {
                    "text": p["text"],
                    "citations": p.get("citations") or [],
                    "meta": p.get("meta") or {},
                }
            )
        if paras:
            verified.append({"heading": section["heading"], "paragraphs": paras})
    state.verified_sections = verified
    state.claims_dropped = dropped
    return state


def _count_section(heading: str, sections: list[dict[str, Any]]) -> int:
    for s in sections:
        if s["heading"] == heading:
            return len(s.get("paragraphs") or [])
    return 0


def render_local(state: State, *, sync_public: bool = True) -> dict[str, Any]:
    profile = state.topics_cfg.get("profile", "Anna Mosaki")
    focus = state.focus_query or (state.topics_cfg.get("focus") or "").strip().split("\n")[0]
    lit_n = _count_section("Literature", state.verified_sections)
    news_n = _count_section("News", state.verified_sections)
    fund_n = _count_section("Fund research", state.verified_sections)

    review = {
        "kind": "personal-review",
        "delivery": "local-only",
        "number": int(date.today().strftime("%Y%m%d")),
        "date": date.today().isoformat(),
        "mode": "live" if state.live_sources_used else "local",
        "title": f"Reading desk — {date.today().isoformat()}",
        "lede": focus or f"Personalized literature & news review for {profile}.",
        "focus_query": state.focus_query or None,
        "focus_keywords": state.focus_keywords or [],
        "profile": profile,
        "matched_topics": state.matched_topics,
        "topics": [
            {"id": t["id"], "label": t.get("label", t["id"]), "weight": t.get("weight", 1.0)}
            for t in (state.topics_cfg.get("topics") or [])
        ],
        "sections": state.verified_sections,
        "stats": {
            "literature_items": lit_n,
            "news_items": news_n,
            "fund_research_items": fund_n,
            "claims_dropped": state.claims_dropped,
            "sources_local": not state.live_sources_used,
            "emailed": False,
            "sources": state.source_stats,
            "items_ingested": len(state.items),
            "items_ranked": len(state.ranked),
            "focus_keywords": state.focus_keywords,
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(review, indent=2)
    OUT.write_text(payload)
    OUT_LEGACY.write_text(payload)
    if sync_public:
        try:
            PUBLIC_COPY.mkdir(parents=True, exist_ok=True)
            (PUBLIC_COPY / "latest-review.json").write_text(payload)
            (PUBLIC_COPY / "latest-issue.json").write_text(payload)
        except OSError:
            pass
    return review


def _langfuse_trace():
    import os

    pk, sk = os.getenv("LANGFUSE_PUBLIC_KEY"), os.getenv("LANGFUSE_SECRET_KEY")
    if not pk or not sk:
        return None
    try:
        from langfuse import Langfuse

        lf = Langfuse(
            public_key=pk,
            secret_key=sk,
            host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
        )
        return lf.trace(
            name="signal-desk-review",
            tags=["signal-desk", "research-digest", os.getenv("LANGFUSE_PROJECT", "anna-portfolio")],
        )
    except Exception:
        return None


async def run_once_async(
    *,
    live: bool = True,
    focus_query: str = "",
    on_progress: ProgressCb | None = None,
) -> dict[str, Any]:
    trace = _langfuse_trace()
    state = State()

    async def emit(etype: str, data: dict[str, Any]) -> None:
        if on_progress:
            result = on_progress(etype, data)
            if hasattr(result, "__await__"):
                await result

    await emit(
        "run.started",
        {
            "live": live,
            "focus": (focus_query or "").strip() or None,
        },
    )
    state = await ingest_async(
        state, live=live, on_progress=on_progress, focus_query=focus_query
    )

    span = None
    if trace is not None:
        try:
            span = trace.span(name="personalize_and_rank")
        except Exception:
            span = None
    state = personalize_and_rank(state)
    await emit(
        "rank.done",
        {
            "ranked": len(state.ranked),
            "topics": state.matched_topics,
            "focus_keywords": state.focus_keywords,
        },
    )
    if span is not None:
        try:
            span.end()
        except Exception:
            pass

    state = synthesize(state)
    await emit("synthesize.done", {"sections": [s["heading"] for s in state.draft_sections]})
    state = verify(state)
    review = render_local(state)

    if trace is not None:
        try:
            trace.update(
                output={
                    "date": review["date"],
                    "dropped": review["stats"]["claims_dropped"],
                    "topics": review["matched_topics"],
                    "mode": review["mode"],
                    "focus": review.get("focus_query"),
                }
            )
        except Exception:
            pass

    # Terminal run.finished is emitted by the API orchestrator after state.review is set,
    # so SSE clients can safely GET /api/run/{id} without a race.
    return review


def run_once(*, live: bool = True, focus_query: str = "") -> dict[str, Any]:
    """CLI / sync entrypoint."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(run_once_async(live=live, focus_query=focus_query))
    # Already in an event loop (e.g. Jupyter) — run in a thread
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(
            lambda: asyncio.run(run_once_async(live=live, focus_query=focus_query))
        ).result()
