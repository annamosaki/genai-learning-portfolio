"""In-memory rate limiter + spend-cap gate. Swap for Redis in production."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from threading import Lock

from .config import get_settings

_lock = Lock()
_hits: dict[tuple[str, str], int] = defaultdict(int)
_day = date.today()


def check_limit(ip: str, demo: str) -> tuple[bool, str]:
    global _day
    settings = get_settings()
    with _lock:
        today = date.today()
        if today != _day:
            _hits.clear()
            _day = today
        if settings.spend_usd_month >= settings.monthly_spend_cap_usd:
            return False, "spend_cap"
        key = (ip, demo)
        _hits[key] += 1
        if _hits[key] > settings.daily_demo_limit_per_ip:
            return False, "rate_limit"
        return True, "ok"


def client_ip(headers: dict[str, str], fallback: str = "local") -> str:
    return headers.get("x-forwarded-for", fallback).split(",")[0].strip()
