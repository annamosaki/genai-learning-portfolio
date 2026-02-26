from datetime import datetime, timezone

from fastapi import APIRouter

from ..config import get_settings
from ..observability import langfuse_status

router = APIRouter(tags=["status"])


@router.get("/status")
def status():
    s = get_settings()
    degraded = s.spend_usd_month >= s.monthly_spend_cap_usd
    return {
        "ok": True,
        "mode": "degraded-replay" if degraded else "live-with-replay",
        "spend_usd_month": s.spend_usd_month,
        "spend_cap_usd": s.monthly_spend_cap_usd,
        "observability": langfuse_status(),
        "demos": [
            {
                "name": "Signal Desk",
                "status": "healthy",
                "last_run": "2026-07-20T06:00:00Z",
                "mode": "local",
            },
            {
                "name": "The Floor",
                "status": "healthy",
                "last_run": datetime.now(timezone.utc).isoformat(),
                "mode": "replay" if degraded or not s.openai_api_key else "live",
            },
            {
                "name": "Verdict",
                "status": "healthy",
                "last_run": "2026-07-24T12:00:00Z",
                "mode": "replay",
            },
            {
                "name": "Horizon",
                "status": "healthy",
                "last_run": "2026-07-24T12:05:00Z",
                "mode": "replay",
            },
        ],
    }
