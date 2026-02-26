import json
from pathlib import Path

from fastapi import APIRouter, Query, Request

from ..rate_limit import check_limit, client_ip

router = APIRouter(tags=["horizon"])

ARTIFACT = (
    Path(__file__).resolve().parents[4]
    / "content"
    / "artifacts"
    / "horizon"
    / "sample-forecast.json"
)


@router.get("/forecast")
async def forecast(
    request: Request,
    ticker: str = Query(default="SPY"),
    horizon: int = Query(default=10, ge=5, le=30),
):
    ip = client_ip(dict(request.headers))
    ok, _ = check_limit(ip, "horizon")
    sample = json.loads(ARTIFACT.read_text())
    series = sample["series"]
    # Trim / pad to requested horizon for the interactive demo.
    hist = [p for p in series if p.get("t", 0) <= 0]
    fut = [p for p in series if p.get("t", 0) > 0][:horizon]
    return {
        "mode": "live" if ok else "replay",
        "ticker": ticker.upper(),
        "horizon": horizon,
        "series": hist + fut,
        "note": "Heavy TSFM inference is offline; this endpoint serves cached/artifact forecasts.",
    }
