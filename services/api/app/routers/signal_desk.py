"""Research Digest — personalized literature & news review (gateway shim)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["signal-desk"])

import os

from ..serverless_runtime import artifact_dir, is_serverless, task_root

if is_serverless():
    ROOT = task_root()
    PROJECT = ROOT / "projects" / "03-research-digest"
    if not PROJECT.exists():
        PROJECT = ROOT  # flattened image layout
    # Match digest-api / pipeline: ARTIFACT_DIR already points at the desk folder.
    _art = Path(os.environ.get("ARTIFACT_DIR") or str(artifact_dir("signal-desk")))
    _art.mkdir(parents=True, exist_ok=True)
    ARTIFACT = _art / "latest-review.json"
    ARTIFACT_LEGACY = _art / "latest-issue.json"
    TOPICS = PROJECT / "topics.yaml"
    PUBLIC_COPY = _art
else:
    ROOT = Path(__file__).resolve().parents[4]
    PROJECT = ROOT / "projects" / "03-research-digest"
    ARTIFACT = ROOT / "content" / "artifacts" / "signal-desk" / "latest-review.json"
    ARTIFACT_LEGACY = ROOT / "content" / "artifacts" / "signal-desk" / "latest-issue.json"
    TOPICS = PROJECT / "topics.yaml"
    PUBLIC_COPY = ROOT / "apps" / "web" / "public" / "artifacts" / "signal-desk"

# Ensure signal_desk is importable when gateway runs from services/api
if str(PROJECT) not in sys.path:
    sys.path.insert(0, str(PROJECT))


def _load_review() -> dict:
    path = ARTIFACT if ARTIFACT.exists() else ARTIFACT_LEGACY
    if not path.exists():
        raise HTTPException(404, "No local review yet. Run regenerate.")
    return json.loads(path.read_text())


def _sync_public(data: dict) -> None:
    PUBLIC_COPY.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, indent=2)
    (PUBLIC_COPY / "latest-review.json").write_text(payload)
    (PUBLIC_COPY / "latest-issue.json").write_text(payload)


@router.get("/latest")
def latest_review():
    data = _load_review()
    data["mode"] = data.get("mode") or "local"
    data["delivery"] = "local-only"
    return data


@router.get("/topics")
def get_topics():
    if not TOPICS.exists():
        raise HTTPException(404, "topics.yaml missing")
    try:
        import yaml

        cfg = yaml.safe_load(TOPICS.read_text()) or {}
    except Exception:
        cfg = {"raw": TOPICS.read_text()}
    return {
        "path": str(TOPICS.relative_to(ROOT)),
        "profile": cfg.get("profile"),
        "focus": cfg.get("focus"),
        "topics": cfg.get("topics", []),
        "rules": cfg.get("rules", {}),
        "free_only": True,
    }


@router.post("/regenerate")
async def regenerate(live: bool = True, focus_query: str = ""):
    """Re-run the digest pipeline (live ArXiv/RSS by default)."""
    try:
        from signal_desk.pipeline import run_once_async

        data = await run_once_async(live=live, focus_query=focus_query)
    except Exception as exc:
        raise HTTPException(500, f"Pipeline failed: {exc}") from exc
    _sync_public(data)
    return {"ok": True, "review": data}
