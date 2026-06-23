"""Local JSONL digests and markdown inbox (offline seed / fallback)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def fetch_local_jsonl(path: Path, *, default_kind: str | None = None) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if default_kind and not row.get("kind"):
            row["kind"] = default_kind
        row.setdefault("source", "local-jsonl")
        rows.append(row)
    return rows


def fetch_local_inbox(folder: Path, kind: str) -> list[dict[str, Any]]:
    if not folder.is_dir():
        return []
    items: list[dict[str, Any]] = []
    for p in sorted(folder.glob("*.md")):
        text = p.read_text(encoding="utf-8")
        title = p.stem.replace("-", " ").title()
        m = re.search(r"^#\s+(.+)$", text, re.M)
        if m:
            title = m.group(1).strip()
        row: dict[str, Any] = {
            "id": f"inbox-{p.stem}",
            "kind": kind,
            "title": title,
            "url": f"file://{p}",
            "topics": [],
            "source": "local-inbox",
        }
        if kind == "literature":
            row["abstract"] = text[:800]
        else:
            row["text"] = text[:800]
        items.append(row)
    return items
