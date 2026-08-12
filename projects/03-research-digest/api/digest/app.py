"""Research Digest API — free ArXiv + RSS (+ optional Finnhub) with SSE regenerate."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sse_starlette import EventSourceResponse

from .events import event_bus, stream_events
from .orchestrator import orchestrator
from .serverless_runtime import is_serverless, task_root

if is_serverless():
    ROOT = task_root()
    PROJECT = task_root()
    # Dockerfile sets ARTIFACT_DIR=/tmp/artifacts/signal-desk (already the desk folder).
    # Do not nest another "signal-desk" segment under it.
    _art = Path(os.environ.get("ARTIFACT_DIR") or "/tmp/artifacts/signal-desk")
    _art.mkdir(parents=True, exist_ok=True)
    ARTIFACT = _art / "latest-review.json"
    ARTIFACT_LEGACY = _art / "latest-issue.json"
    TOPICS = PROJECT / "topics.yaml"
    # Seed writable /tmp from the image-baked copy on cold start.
    _seed = PROJECT / "content" / "artifacts" / "signal-desk"
    for name in ("latest-review.json", "latest-issue.json"):
        dest = _art / name
        src = _seed / name
        if not dest.exists() and src.exists():
            dest.write_text(src.read_text())
else:
    ROOT = Path(__file__).resolve().parents[4]  # repo root (local monorepo)
    PROJECT = Path(__file__).resolve().parents[2]  # projects/03-research-digest
    ARTIFACT = ROOT / "content" / "artifacts" / "signal-desk" / "latest-review.json"
    ARTIFACT_LEGACY = ROOT / "content" / "artifacts" / "signal-desk" / "latest-issue.json"
    TOPICS = PROJECT / "topics.yaml"

# Load repo-root .env so FINNHUB_API_KEY / Langfuse work even when not exported by the shell.
try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env", override=False)
except Exception:
    pass

app = FastAPI(
    title="Research Digest API",
    description="Personalized literature, news & fund-research digest (free sources)",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RunRequest(BaseModel):
    live: bool = Field(default=True, description="Fetch ArXiv/RSS/Finnhub when true")
    focus_query: str = Field(
        default="",
        max_length=400,
        description="Domain / keywords that steer ArXiv queries and ranking for this run",
    )
    notify_subscribers: bool = Field(
        default=True,
        description="After a successful live run, email the condensed newsletter to active subscribers",
    )


class SubscribeRequest(BaseModel):
    email: str = Field(..., max_length=254)


class SendOneRequest(BaseModel):
    email: str = Field(..., max_length=254)


def _load_review() -> dict:
    path = ARTIFACT if ARTIFACT.exists() else ARTIFACT_LEGACY
    if not path.exists():
        raise HTTPException(404, "No review yet. Run regenerate.")
    return json.loads(path.read_text())


@app.get("/")
async def root():
    return {
        "name": "Research Digest API",
        "version": "1.0.0",
        "demo": "/demos/research-digest",
    }


@app.get("/health")
@app.get("/api/health")
async def health():
    return {"status": "healthy", "ok": True}


@app.get("/api/latest")
async def latest_review():
    data = _load_review()
    data["delivery"] = "local-only"
    return data


@app.get("/api/topics")
async def get_topics():
    if not TOPICS.exists():
        raise HTTPException(404, "topics.yaml missing")
    try:
        import yaml

        cfg = yaml.safe_load(TOPICS.read_text()) or {}
    except Exception:
        cfg = {"raw": TOPICS.read_text()}
    return {
        "path": "projects/03-research-digest/topics.yaml",
        "profile": cfg.get("profile"),
        "focus": cfg.get("focus"),
        "topics": cfg.get("topics", []),
        "rules": cfg.get("rules", {}),
        "sources": {
            "literature": [s.get("name") for s in (cfg.get("sources") or {}).get("literature", [])],
            "news": [s.get("name") for s in (cfg.get("sources") or {}).get("news", [])],
            "fund_research": [
                s.get("name") for s in (cfg.get("sources") or {}).get("fund_research", [])
            ],
        },
        "free_only": True,
    }


@app.post("/api/run")
async def start_run(request: Optional[RunRequest] = None) -> Dict[str, Any]:
    live = True if request is None else bool(request.live)
    focus_query = "" if request is None else (request.focus_query or "").strip()
    notify = True if request is None else bool(request.notify_subscribers)
    run_id = await orchestrator.start_run(
        live=live, focus_query=focus_query, notify_subscribers=notify
    )
    return {
        "run_id": run_id,
        "status": "started",
        "live": live,
        "focus_query": focus_query or None,
        "notify_subscribers": notify,
    }


@app.get("/api/run/{run_id}/stream")
async def stream_run(run_id: str):
    run_state = orchestrator.get_run_state(run_id)
    if not run_state:
        raise HTTPException(status_code=404, detail="Run not found")
    if not run_state.started:
        await orchestrator.ensure_started(run_id)
    return EventSourceResponse(stream_events(run_id, event_bus))


@app.get("/api/run/{run_id}")
async def get_run(run_id: str):
    run_state = orchestrator.get_run_state(run_id)
    if not run_state:
        raise HTTPException(status_code=404, detail="Run not found")
    return {
        "run_id": run_id,
        "status": run_state.status,
        "live": run_state.live,
        "focus_query": run_state.focus_query or None,
        "error": run_state.error,
        "review": run_state.review,
        "newsletter": run_state.newsletter,
    }


@app.post("/api/newsletter/subscribe")
async def newsletter_subscribe(request: SubscribeRequest):
    from .newsletter import subscribe

    try:
        return subscribe(request.email)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.get("/api/newsletter/confirm")
async def newsletter_confirm(email: str, token: str):
    from .newsletter import confirm

    try:
        result = confirm(email, token)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return result


@app.get("/api/newsletter/unsubscribe")
async def newsletter_unsubscribe(email: str, token: str):
    from .newsletter import unsubscribe

    try:
        return unsubscribe(email, token)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/newsletter/send")
async def newsletter_send():
    """Send condensed newsletter of the latest review to all active subscribers."""
    from .newsletter import dispatch_newsletter

    review = _load_review()
    return dispatch_newsletter(review)


@app.post("/api/newsletter/send-one")
async def newsletter_send_one(request: SendOneRequest):
    """One-shot: email the latest condensed digest to a single address (also useful in SES sandbox)."""
    from .newsletter import send_one_shot

    review = _load_review()
    try:
        return send_one_shot(request.email, review)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
