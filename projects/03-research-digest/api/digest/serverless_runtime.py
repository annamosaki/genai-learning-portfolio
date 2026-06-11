"""Shared serverless helpers for Lambda (paths, DynamoDB run/approval store)."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Optional


def is_serverless() -> bool:
    return bool(os.environ.get("AWS_LAMBDA_FUNCTION_NAME") or os.environ.get("SERVERLESS") == "1")


def task_root() -> Path:
    if os.environ.get("LAMBDA_TASK_ROOT"):
        return Path(os.environ["LAMBDA_TASK_ROOT"])
    # Fall back: walk up looking for content/ or topics.yaml markers
    here = Path(__file__).resolve()
    for p in [here.parent, *here.parents]:
        if (p / "content").is_dir() or (p / "topics.yaml").exists():
            return p
    return Path.cwd()


def artifact_dir(*parts: str) -> Path:
    base = os.environ.get("ARTIFACT_DIR")
    if base:
        path = Path(base)
    elif is_serverless():
        path = Path("/tmp/artifacts")
    else:
        path = task_root() / "content" / "artifacts"
    path = path.joinpath(*parts) if parts else path
    path.mkdir(parents=True, exist_ok=True)
    return path


class RunStore:
    """Optional DynamoDB-backed store for cross-invocation run/approval state."""

    def __init__(self) -> None:
        self.table_name = os.environ.get("RUNS_TABLE", "").strip()
        self._table = None

    @property
    def enabled(self) -> bool:
        return bool(self.table_name)

    def _get_table(self):
        if self._table is None:
            import boto3

            self._table = boto3.resource("dynamodb").Table(self.table_name)
        return self._table

    def put(self, pk: str, sk: str, data: dict[str, Any], ttl_hours: int = 24) -> None:
        if not self.enabled:
            return
        item = {
            "pk": pk,
            "sk": sk,
            "ttl": int(time.time()) + ttl_hours * 3600,
            "data": json.dumps(data, default=str),
        }
        self._get_table().put_item(Item=item)

    def get(self, pk: str, sk: str) -> Optional[dict[str, Any]]:
        if not self.enabled:
            return None
        resp = self._get_table().get_item(Key={"pk": pk, "sk": sk})
        item = resp.get("Item")
        if not item:
            return None
        raw = item.get("data")
        if isinstance(raw, str):
            return json.loads(raw)
        return raw  # type: ignore[return-value]


run_store = RunStore()
