"""OHLCV loading and quantitative indicators."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from ..config import settings
from .yfinance_tools import get_price_history


def _parse_history_payload(data: Any) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    if isinstance(data, str) and "|" in data:
        for line in data.splitlines():
            line = line.strip()
            if not line.startswith("|") or line.startswith("|:"):
                continue
            if "Date" in line and "Open" in line:
                continue
            parts = [p.strip() for p in line.strip("|").split("|")]
            if len(parts) < 6:
                continue
            try:
                rows.append(
                    {
                        "Date": parts[0][:10],
                        "Open": float(parts[1]),
                        "High": float(parts[2]),
                        "Low": float(parts[3]),
                        "Close": float(parts[4]),
                        "Volume": float(parts[5].replace("e+", "E")),
                    }
                )
            except (TypeError, ValueError):
                continue
        return rows

    if isinstance(data, list):
        records = data
    elif isinstance(data, dict):
        records = data.get("history") or data.get("data") or data.get("prices") or []
    else:
        records = []

    for row in records:
        if not isinstance(row, dict):
            continue
        try:
            rows.append(
                {
                    "Date": str(
                        row.get("Date") or row.get("date") or row.get("Datetime") or ""
                    )[:10],
                    "Open": float(row.get("Open") or row.get("open") or 0),
                    "High": float(row.get("High") or row.get("high") or 0),
                    "Low": float(row.get("Low") or row.get("low") or 0),
                    "Close": float(row.get("Close") or row.get("close") or 0),
                    "Volume": float(row.get("Volume") or row.get("volume") or 0),
                }
            )
        except (TypeError, ValueError):
            continue
    return rows


def _load_csv(ticker: str) -> Optional[List[Dict[str, Any]]]:
    path = Path(settings.prices_dir) / f"{ticker.upper()}.csv"
    if not path.exists():
        return None
    rows: List[Dict[str, Any]] = []
    with path.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(
                {
                    "Date": row.get("Date") or row.get("date"),
                    "Open": float(row.get("Open") or row.get("open") or 0),
                    "High": float(row.get("High") or row.get("high") or 0),
                    "Low": float(row.get("Low") or row.get("low") or 0),
                    "Close": float(row.get("Close") or row.get("close") or 0),
                    "Volume": float(row.get("Volume") or row.get("volume") or 0),
                }
            )
    rows.sort(key=lambda r: r["Date"] or "")
    return rows


async def load_ohlcv(
    ticker: str, period: str = "6mo", interval: str = "1d"
) -> dict[str, Any]:
    """Load OHLCV — live market data first, CSV cache fallback."""
    ticker = ticker.upper()
    live = await get_price_history(ticker, period=period, interval=interval)
    if live.get("ok"):
        rows = _parse_history_payload(live.get("data"))
        if rows:
            return {
                "ok": True,
                "ticker": ticker,
                "rows": rows,
                "source": live.get("_transport", "live"),
                "count": len(rows),
            }

    csv_rows = _load_csv(ticker)
    if csv_rows:
        return {
            "ok": True,
            "ticker": ticker,
            "rows": csv_rows,
            "source": "local_csv",
            "count": len(csv_rows),
            "live_error": live.get("error"),
        }

    return {
        "ok": False,
        "ticker": ticker,
        "error": live.get("error") or "No price data available",
        "rows": [],
    }


def _sma(arr: np.ndarray, window: int) -> Optional[float]:
    if len(arr) < window:
        return None
    return float(np.mean(arr[-window:]))


def _rsi(closes: np.ndarray, window: int = 14) -> Optional[float]:
    if len(closes) < window + 1:
        return None
    delta = np.diff(closes)
    gains = np.where(delta > 0, delta, 0.0)
    losses = np.where(delta < 0, -delta, 0.0)
    avg_gain = float(np.mean(gains[-window:]))
    avg_loss = float(np.mean(losses[-window:]))
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def compute_indicators(rows: List[Dict[str, Any]]) -> dict[str, Any]:
    """Compute technical and risk metrics from OHLCV rows."""
    if not rows:
        return {"ok": False, "error": "No rows"}

    closes = np.array([r["Close"] for r in rows], dtype=float)
    highs = np.array([r["High"] for r in rows], dtype=float)
    lows = np.array([r["Low"] for r in rows], dtype=float)
    volumes = np.array([r["Volume"] for r in rows], dtype=float)
    dates = [r["Date"] for r in rows]

    sma20 = _sma(closes, 20)
    mid = sma20
    std = float(np.std(closes[-20:])) if len(closes) >= 20 else None
    bb_upper = mid + 2 * std if mid is not None and std is not None else None
    bb_lower = mid - 2 * std if mid is not None and std is not None else None
    bb_pos = None
    if bb_upper and bb_lower and bb_upper != bb_lower:
        bb_pos = float((closes[-1] - bb_lower) / (bb_upper - bb_lower))

    rets = np.diff(closes) / closes[:-1] if len(closes) > 1 else np.array([0.0])
    vol = float(np.std(rets)) if len(rets) else 0.0
    peak = np.maximum.accumulate(closes)
    dd = (closes - peak) / peak

    def ret(n: int) -> float:
        if len(closes) <= n:
            return 0.0
        return float(closes[-1] / closes[-(n + 1)] - 1)

    avg_vol = float(np.mean(volumes[-30:])) if len(volumes) else 0.0

    return {
        "ok": True,
        "period": {"start": dates[0] if dates else None, "end": dates[-1] if dates else None, "bars": len(dates)},
        "technical": {
            "current_price": float(closes[-1]),
            "sma_10": _sma(closes, 10),
            "sma_20": sma20,
            "sma_50": _sma(closes, 50),
            "rsi_14": _rsi(closes),
            "bb_upper": bb_upper,
            "bb_lower": bb_lower,
            "bb_position": bb_pos,
            "period_high": float(np.max(highs[-30:])) if len(highs) else float(closes[-1]),
            "period_low": float(np.min(lows[-30:])) if len(lows) else float(closes[-1]),
        },
        "risk": {
            "volatility_daily": vol,
            "volatility_annualized": vol * float(np.sqrt(252)),
            "avg_daily_return": float(np.mean(rets)) if len(rets) else 0.0,
            "annualized_return": float(np.mean(rets) * 252) if len(rets) else 0.0,
            "sharpe_ratio": (float(np.mean(rets) * 252) / (vol * float(np.sqrt(252))))
            if vol > 0
            else 0.0,
            "max_drawdown": float(np.min(dd)) if len(dd) else 0.0,
            "var_95": float(np.percentile(rets, 5)) if len(rets) else 0.0,
            "positive_days": float(np.mean(rets > 0)) if len(rets) else 0.0,
        },
        "momentum": {
            "return_5d": ret(5),
            "return_20d": ret(20),
            "price_percentile": float(np.mean(closes <= closes[-1])) if len(closes) else 0.0,
            "volume_vs_avg_30d": float(volumes[-1] / avg_vol) if avg_vol else 0.0,
        },
    }
