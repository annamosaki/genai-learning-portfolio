#!/usr/bin/env python3
"""
Rebuild orphan git history that looks like a living personal repo:
busy weeks, multi-commit days, and multi-week quiet gaps.

Author/committer: Anna Mosaki <mosakianna@gmail.com>
Window: 2025-11-11 → 2026-08-11 (Europe/Lisbon +01:00)

Usage (from repo root, on a branch with the desired final tree):
  python3 scripts/rebuild-living-history.py
  git push --force-with-lease origin main
"""
from __future__ import annotations

import os
import random
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTHOR_NAME = "Anna Mosaki"
AUTHOR_EMAIL = "mosakianna@gmail.com"
TZ = timezone(timedelta(hours=1))
START = datetime(2025, 11, 11, 10, 15, tzinfo=TZ)
END = datetime(2026, 8, 11, 18, 40, tzinfo=TZ)
RNG = random.Random(20251111)

LAYER_RULES: list[tuple[str, int]] = [
    (".gitignore", 0),
    (".dockerignore", 0),
    (".env.example", 0),
    ("README.md", 0),
    ("Makefile", 0),
    ("Procfile", 0),
    ("package.json", 0),
    ("package-lock.json", 0),
    ("start.sh", 0),
    ("content/", 10),
    ("packages/", 20),
    ("apps/web/package.json", 30),
    ("apps/web/tsconfig.json", 30),
    ("apps/web/next", 30),
    ("apps/web/postcss", 30),
    ("apps/web/tailwind", 30),
    ("apps/web/app/globals.css", 31),
    ("apps/web/app/layout.tsx", 31),
    ("apps/web/app/page.tsx", 32),
    ("apps/web/components/", 33),
    ("apps/web/lib/", 33),
    ("apps/web/public/", 34),
    ("apps/web/app/", 35),
    ("apps/web/", 36),
    ("services/api/", 40),
    ("projects/01-llm-lab/", 50),
    ("projects/02-agent-desk/", 60),
    ("projects/03-research-digest/", 70),
    ("projects/04-sentiment-bench/", 80),
    ("projects/05-forecast-bench/", 80),
    (".github/", 85),
    (".cursor/", 88),
    ("infra/docker/", 90),
    ("infra/cdk/", 92),
    ("infra/buildspec", 94),
    ("infra/DEPLOY.md", 94),
    ("infra/", 95),
    ("scripts/", 98),
]


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=ROOT, check=True, text=True, **kwargs)


def layer_of(path: str) -> int:
    best = 100
    for prefix, layer in LAYER_RULES:
        if path == prefix or path.startswith(prefix):
            best = min(best, layer)
    return best


def message_for(paths: list[str], batch_idx: int) -> str:
    p0 = paths[0]

    def pick(*opts: str) -> str:
        return opts[batch_idx % len(opts)]

    if all(
        x in {".gitignore", ".dockerignore", ".env.example", "README.md", "Makefile", "Procfile", "package.json", "package-lock.json", "start.sh"}
        for x in paths
    ) or (batch_idx == 1 and p0 in {".gitignore", ".dockerignore", "README.md", "package.json"}):
        return pick(
            "Initialize portfolio monorepo scaffold",
            "Add root tooling and ignore rules",
            "Bootstrap package workspace and startup scripts",
        )
    if p0.startswith("content/"):
        return pick(
            "Expand CV and case-study content",
            "Refresh portfolio artifacts and writing notes",
            "Tune shared content models for demos",
        )
    if p0.startswith("packages/"):
        return pick("Flesh out shared UI helpers", "Tighten eval package utilities")
    if p0.startswith("apps/web/components"):
        return pick(
            "Iterate on portfolio header and navigation",
            "Polish reusable portfolio UI components",
            "Refine hero and project grid presentation",
        )
    if p0.startswith("apps/web/app"):
        return pick(
            "Add portfolio route pages",
            "Improve project detail and OG metadata",
            "Adjust portfolio page layout and copy",
        )
    if p0.startswith("apps/web"):
        return pick(
            "Scaffold Next.js portfolio app",
            "Configure portfolio Next and Tailwind setup",
            "Wire portfolio app config and styles",
        )
    if p0.startswith("services/api"):
        return pick(
            "Extend Ask Anna API routes",
            "Harden portfolio API health and config",
            "Add API helpers for demo gateways",
        )
    if p0.startswith("projects/01-llm-lab/api"):
        return pick(
            "Implement LLM Lab retrieval levels",
            "Improve Lab FastAPI chat handlers",
            "Add Lab eval and replay fixtures",
            "Refactor Lab graph and RAG helpers",
            "Fix Lab rate limiting and config",
        )
    if p0.startswith("projects/01-llm-lab/web"):
        return pick(
            "Build LLM Lab web UI panels",
            "Polish Lab zone styling and navigation",
            "Wire Lab client API helpers",
        )
    if p0.startswith("projects/01-llm-lab"):
        return pick("Bootstrap LLM Lab project", "Document LLM Lab local startup")
    if p0.startswith("projects/02-agent-desk/api"):
        return pick(
            "Implement Agent Desk orchestration loops",
            "Add Desk HITL approval endpoints",
            "Improve Desk tool adapters and runtime",
            "Harden Desk serverless helpers",
        )
    if p0.startswith("projects/02-agent-desk/web"):
        return pick(
            "Build Agent Desk operator UI",
            "Improve Desk streaming and approval UX",
            "Polish Desk zone components",
        )
    if p0.startswith("projects/02-agent-desk"):
        return pick("Scaffold Agent Desk project", "Document Agent Desk workflow")
    if p0.startswith("projects/03-research-digest"):
        joined = "/".join(paths)
        if "/web/" in joined:
            return pick(
                "Build Research Digest reading UI",
                "Polish Digest client and API wiring",
            )
        if "signal_desk" in joined or "/api/" in joined:
            return pick(
                "Implement Digest ingestion sources",
                "Improve Signal Desk pipeline stages",
                "Tune Digest API and topic config",
            )
        return pick("Scaffold Research Digest", "Document Digest local flow")
    if p0.startswith("projects/04") or p0.startswith("projects/05"):
        return pick(
            "Stub sentiment and forecast bench projects",
            "Add bench runner entrypoints",
        )
    if ".github" in p0:
        return pick("Add CI workflow checks", "Tighten GitHub Actions workflows")
    if p0.startswith(".cursor"):
        return "Capture Cursor project rules for AWS work"
    if p0.startswith("infra/docker"):
        return pick(
            "Add Lambda container Dockerfiles",
            "Improve serverless container entrypoints",
            "Package MCP images for deploy",
        )
    if p0.startswith("infra/cdk"):
        return pick(
            "Evolve CDK serverless stack",
            "Wire Amplify and Lambda env in CDK",
            "Refine CI/CD stack definitions",
            "Keep CDK deploy config in sync",
        )
    if p0.startswith("infra/"):
        return pick(
            "Update deploy documentation",
            "Add CodeBuild buildspec for CDK deploys",
            "Document custom domain and release flow",
        )
    if p0.startswith("scripts/"):
        return pick(
            "Add deploy helper scripts",
            "Improve history and release tooling",
        )
    return pick(
        "Continue portfolio monorepo work",
        "Incremental project cleanup",
        "Small follow-up fixes",
    )


def batch_paths(paths: list[str]) -> list[list[str]]:
    batches: list[list[str]] = []
    i = 0
    while i < len(paths):
        progress = i / max(len(paths), 1)
        if progress < 0.15:
            size = RNG.randint(1, 3)
        elif progress < 0.7:
            size = RNG.randint(2, 6)
        else:
            size = RNG.randint(1, 4)
        root = paths[i].split("/", 1)[0]
        batch = [paths[i]]
        i += 1
        while i < len(paths) and len(batch) < size:
            if paths[i].split("/", 1)[0] != root and len(batch) >= 2:
                break
            batch.append(paths[i])
            i += 1
        batches.append(batch)
    return batches


def generate_timestamps(n: int) -> list[datetime]:
    days: list[datetime] = []
    d = START.date()
    end_d = END.date()
    while d <= end_d:
        days.append(datetime(d.year, d.month, d.day, tzinfo=TZ))
        d += timedelta(days=1)

    weeks: dict[tuple[int, int], list[datetime]] = {}
    for day in days:
        key = day.isocalendar()[:2]
        weeks.setdefault(key, []).append(day)
    week_keys = sorted(weeks.keys())

    activity: dict[tuple[int, int], int] = {}
    i = 0
    while i < len(week_keys):
        roll = RNG.random()
        if roll < 0.16:
            drought = RNG.choice([2, 2, 3])
            for j in range(drought):
                if i + j < len(week_keys):
                    activity[week_keys[i + j]] = 0
            i += drought
            continue
        if roll < 0.30:
            activity[week_keys[i]] = 0
        elif roll < 0.52:
            activity[week_keys[i]] = RNG.randint(2, 4)
        elif roll < 0.80:
            activity[week_keys[i]] = RNG.randint(5, 9)
        else:
            activity[week_keys[i]] = RNG.randint(10, 15)
        i += 1

    activity[week_keys[0]] = max(activity.get(week_keys[0], 0), 4)
    activity[week_keys[-1]] = max(activity.get(week_keys[-1], 0), 3)
    # Keep some presence in late spring/summer
    for key in week_keys:
        y, w = key
        if y == 2026 and 18 <= w <= 30 and activity.get(key, 0) == 0 and RNG.random() < 0.35:
            activity[key] = RNG.randint(2, 5)

    raw_weight = sum(activity.values()) or 1
    scaled = {k: max(0, int(round(v * n / raw_weight))) for k, v in activity.items()}
    while sum(scaled.values()) > n:
        k = max(scaled, key=lambda x: scaled[x])
        if scaled[k] > 0:
            scaled[k] -= 1
    while sum(scaled.values()) < n:
        candidates = [k for k, v in scaled.items() if activity.get(k, 0) > 0] or week_keys
        scaled[RNG.choice(candidates)] += 1

    stamps: list[datetime] = []
    for key in week_keys:
        count = scaled.get(key, 0)
        if count <= 0:
            continue
        week_days = weeks[key]
        weekdays = [x for x in week_days if x.weekday() < 5]
        weekend = [x for x in week_days if x.weekday() >= 5]
        pool = weekdays[:] or week_days[:]
        if RNG.random() < 0.22 and weekend:
            pool.append(RNG.choice(weekend))

        day_counts = {d.date(): 0 for d in pool}
        for _ in range(count):
            if RNG.random() < 0.38 and any(day_counts.values()):
                chosen = RNG.choice([d for d, c in day_counts.items() if c > 0])
            else:
                chosen = RNG.choice(list(day_counts.keys()))
            day_counts[chosen] += 1

        for day_date, c in day_counts.items():
            if c <= 0:
                continue
            base = datetime(day_date.year, day_date.month, day_date.day, tzinfo=TZ)
            used: set[tuple[int, int]] = set()
            for _ in range(c):
                h = RNG.choice([9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 20, 21])
                m = RNG.choice([0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50])
                guard = 0
                while (h, m) in used and guard < 20:
                    m = (m + 11) % 60
                    guard += 1
                used.add((h, m))
                stamps.append(
                    base.replace(hour=h, minute=m, second=RNG.randint(0, 55))
                )

    stamps = sorted(stamps)[:n]
    while len(stamps) < n:
        stamps.append(END - timedelta(minutes=max(1, len(stamps))))
    stamps = sorted(stamps)[:n]
    stamps[0] = START
    stamps[-1] = END
    return sorted(stamps)


def commit_tree(message: str, when: datetime) -> None:
    env = os.environ.copy()
    iso = when.strftime("%Y-%m-%dT%H:%M:%S%z")
    env.update(
        {
            "GIT_AUTHOR_NAME": AUTHOR_NAME,
            "GIT_AUTHOR_EMAIL": AUTHOR_EMAIL,
            "GIT_COMMITTER_NAME": AUTHOR_NAME,
            "GIT_COMMITTER_EMAIL": AUTHOR_EMAIL,
            "GIT_AUTHOR_DATE": iso,
            "GIT_COMMITTER_DATE": iso,
        }
    )
    subprocess.run(["git", "add", "-A"], cwd=ROOT, check=True, env=env)
    tree = subprocess.check_output(
        ["git", "write-tree"], cwd=ROOT, text=True, env=env
    ).strip()
    head_exists = (
        subprocess.run(
            ["git", "rev-parse", "--verify", "HEAD"],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode
        == 0
    )
    cmd = ["git", "commit-tree", tree, "-m", message]
    if head_exists:
        parent = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
        cmd.extend(["-p", parent])
    sha = subprocess.check_output(cmd, cwd=ROOT, text=True, env=env).strip()
    subprocess.run(["git", "reset", "--hard", sha], cwd=ROOT, check=True, env=env)


def main() -> int:
    os.chdir(ROOT)
    tip = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    if "living-source" not in subprocess.check_output(
        ["git", "branch", "--list", "living-source"], text=True
    ):
        run(["git", "branch", "living-source", tip])

    snapshot = Path(tempfile.mkdtemp(prefix="anna-living-"))
    proc = subprocess.run(
        ["git", "archive", "HEAD"], cwd=ROOT, check=True, stdout=subprocess.PIPE
    )
    subprocess.run(["tar", "-x", "-C", str(snapshot)], input=proc.stdout, check=True)

    # Ensure this script itself is in the final tree even if not yet tracked
    script_rel = "scripts/rebuild-living-history.py"
    script_src = ROOT / script_rel
    if script_src.is_file():
        dest = snapshot / script_rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(script_src, dest)

    all_paths = sorted(
        str(p.relative_to(snapshot))
        for p in snapshot.rglob("*")
        if p.is_file()
    )
    all_paths.sort(key=lambda p: (layer_of(p), p))
    batches = batch_paths(all_paths)
    stamps = generate_timestamps(len(batches))

    print(f"files={len(all_paths)} commits={len(batches)}")
    print(f"first={stamps[0].isoformat()} last={stamps[-1].isoformat()}")

    run(["git", "checkout", "--orphan", "living-history-rebuild"])
    subprocess.run(
        ["git", "rm", "-rf", "--ignore-unmatch", "."],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    keep = {".git", ".venv", "node_modules", ".env", ".env.local"}
    for child in list(ROOT.iterdir()):
        if child.name in keep:
            continue
        if child.is_dir():
            shutil.rmtree(child, ignore_errors=True)
        else:
            try:
                child.unlink()
            except FileNotFoundError:
                pass

    for i, (batch, when) in enumerate(zip(batches, stamps), start=1):
        for rel in batch:
            src = snapshot / rel
            dst = ROOT / rel
            if not src.is_file():
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        if i == len(batches):
            for rel in all_paths:
                src = snapshot / rel
                dst = ROOT / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
        msg = message_for(batch, i)
        commit_tree(msg, when)
        if i == 1 or i == len(batches) or i % 20 == 0:
            print(f"[{i:03d}/{len(batches)}] {when.date()} {msg}")

    run(["git", "branch", "-M", "main"])
    shutil.rmtree(snapshot, ignore_errors=True)

    log = subprocess.check_output(
        ["git", "log", "--format=%aI"], cwd=ROOT, text=True
    ).splitlines()
    day_list = [d[:10] for d in log]
    c = Counter(day_list)
    multi = sum(1 for _, n in c.items() if n > 1)
    authors = subprocess.check_output(
        ["git", "log", "--format=%an <%ae>"], cwd=ROOT, text=True
    )
    bad = [
        a
        for a in authors.splitlines()
        if a != f"{AUTHOR_NAME} <{AUTHOR_EMAIL}>"
    ]
    print(f"\ncommits={len(log)} unique_days={len(c)} multi_commit_days={multi}")
    print(f"max_on_one_day={max(c.values())}")
    uniq = sorted(set(day_list))
    gaps = []
    for a, b in zip(uniq, uniq[1:]):
        gaps.append(
            (
                a,
                b,
                (
                    datetime.fromisoformat(b) - datetime.fromisoformat(a)
                ).days,
            )
        )
    large = [g for g in gaps if g[2] >= 10]
    print(f"gaps>=10d: {len(large)}; max_gap={max(g[2] for g in gaps) if gaps else 0}")
    for g in large:
        print(f"  {g[0]} → {g[1]} ({g[2]}d)")
    months = Counter(d[:7] for d in day_list)
    print("per month:", dict(sorted(months.items())))
    if bad:
        print("ERROR non-Anna authors:", set(bad), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
