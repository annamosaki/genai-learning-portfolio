"""Free live + local source fetchers for Research Digest."""

from __future__ import annotations

from .arxiv import fetch_arxiv
from .finnhub import fetch_finnhub
from .local import fetch_local_inbox, fetch_local_jsonl
from .rss import fetch_rss

__all__ = [
    "fetch_arxiv",
    "fetch_finnhub",
    "fetch_local_inbox",
    "fetch_local_jsonl",
    "fetch_rss",
]
