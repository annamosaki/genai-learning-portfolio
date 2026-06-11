"""Research Digest API — free ArXiv + RSS (+ optional Finnhub) with SSE regenerate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sse_starlette import EventSourceResponse

from .events import event_bus, stream_events
from .orchestrator import orchestrator
from .serverless_runtime import artifact_dir, is_serverless, task_root

if is_serverless():
    ROOT = task_root()
    PROJECT = task_root()
    ARTIFACT = artifact_dir("signal-desk") / "latest-review.json"
    ARTIFACT_LEGACY = artifact_dir("signal-desk") / "latest-issue.json"
    TOPICS = PROJECT / "topics.yaml"
else:
    ROOT = Path(__file__).resolve().parents[4]  # repo root (local monorepo)
    PROJECT = Path(__file__).resolve().parents[2]  # projects/03-research-digest
    ARTIFACT = ROOT / "content" / "artifacts" / "signal-desk" / "latest-review.json"
    ARTIFACT_LEGACY = ROOT / "content" / "artifacts" / "signal-desk" / "latest-issue.json"
    TOPICS = PROJECT / "topics.yaml"

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
    run_id = await orchestrator.start_run(live=live)
    return {"run_id": run_id, "status": "started", "live": live}


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
        "error": run_state.error,
        "review": run_state.review,
    }
