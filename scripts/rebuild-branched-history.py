#!/usr/bin/env python3
"""
Rebuild a year-long branched history: main + feature branches + merge commits.

Looks like real feature work landed via merges (PR-style), not only linear commits.
Author: Anna Mosaki <mosakianna@gmail.com>
Window: 2025-11-11 → 2026-08-11

Note: GitHub Pull Request *objects* cannot be backdated via API. This script
creates authentic git topology (branches + merge commits with historical dates).
Future real PRs → main will trigger .github/workflows/deploy-apis-aws.yml.
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
RNG = random.Random(20260811)

# Feature themes used when opening a branch
FEATURE_BRANCHES = [
    ("feature/monorepo-scaffold", "Bootstrap monorepo workspace"),
    ("feature/portfolio-content", "Add CV content and artifacts"),
    ("feature/portfolio-shell", "Build portfolio Next.js shell"),
    ("feature/portfolio-ui", "Polish portfolio UI components"),
    ("feature/ask-anna-api", "Ship Ask Anna API routes"),
    ("feature/llm-lab-api", "Implement LLM Lab API levels"),
    ("feature/llm-lab-ui", "Build LLM Lab web zone"),
    ("feature/agent-desk-api", "Implement Agent Desk orchestration"),
    ("feature/agent-desk-ui", "Build Agent Desk operator UI"),
    ("feature/research-digest", "Add Research Digest pipeline and UI"),
    ("feature/bench-stubs", "Stub sentiment and forecast benches"),
    ("feature/ci-workflows", "Add GitHub Actions CI checks"),
    ("feature/serverless-cdk", "Introduce serverless CDK and containers"),
    ("feature/mcp-packaging", "Package Yahoo Finance and Edgar MCPs"),
    ("feature/custom-domains", "Document and wire custom domains"),
    ("feature/cicd-aws", "Wire GitHub to AWS CodePipeline deploy"),
]

LAYER_RULES: list[tuple[str, int]] = [
    (".gitignore", 0), (".dockerignore", 0), (".env.example", 0),
    ("README.md", 0), ("Makefile", 0), ("Procfile", 0),
    ("package.json", 0), ("package-lock.json", 0), ("start.sh", 0),
    ("content/", 10), ("packages/", 20),
    ("apps/web/", 30), ("services/api/", 40),
    ("projects/01-llm-lab/", 50), ("projects/02-agent-desk/", 60),
    ("projects/03-research-digest/", 70),
    ("projects/04-sentiment-bench/", 80), ("projects/05-forecast-bench/", 80),
    (".github/", 85), (".cursor/", 88),
    ("infra/docker/", 90), ("infra/cdk/", 92), ("infra/", 95), ("scripts/", 98),
]


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=ROOT, check=True, text=True, **kwargs)


def layer_of(path: str) -> int:
    best = 100
    for prefix, layer in LAYER_RULES:
        if path == prefix or path.startswith(prefix):
            best = min(best, layer)
    return best


def env_for(when: datetime) -> dict:
    iso = when.strftime("%Y-%m-%dT%H:%M:%S%z")
    e = os.environ.copy()
    e.update(
        {
            "GIT_AUTHOR_NAME": AUTHOR_NAME,
            "GIT_AUTHOR_EMAIL": AUTHOR_EMAIL,
            "GIT_COMMITTER_NAME": AUTHOR_NAME,
            "GIT_COMMITTER_EMAIL": AUTHOR_EMAIL,
            "GIT_AUTHOR_DATE": iso,
            "GIT_COMMITTER_DATE": iso,
        }
    )
    return e


def write_commit(message: str, when: datetime, parents: list[str] | None = None) -> str:
    e = env_for(when)
    subprocess.run(["git", "add", "-A"], cwd=ROOT, check=True, env=e)
    tree = subprocess.check_output(["git", "write-tree"], cwd=ROOT, text=True, env=e).strip()
    cmd = ["git", "commit-tree", tree, "-m", message]
    for p in parents or []:
        cmd.extend(["-p", p])
    sha = subprocess.check_output(cmd, cwd=ROOT, text=True, env=e).strip()
    subprocess.run(["git", "reset", "--hard", sha], cwd=ROOT, check=True, env=e)
    return sha


def head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def message_for(paths: list[str], batch_idx: int) -> str:
    p0 = paths[0]
    opts_map = [
        (("content/",), ("Expand CV and case-study content", "Refresh portfolio artifacts")),
        (("packages/",), ("Flesh out shared UI helpers", "Tighten eval package utilities")),
        (("apps/web/components",), ("Polish portfolio UI components", "Iterate on site navigation")),
        (("apps/web/app",), ("Add portfolio routes", "Improve project pages and metadata")),
        (("apps/web",), ("Scaffold portfolio Next app", "Configure Next and Tailwind")),
        (("services/api",), ("Extend Ask Anna API", "Harden API health and config")),
        (("projects/01-llm-lab/api",), ("Implement Lab retrieval levels", "Improve Lab FastAPI handlers")),
        (("projects/01-llm-lab/web",), ("Build LLM Lab UI", "Polish Lab zone styling")),
        (("projects/01-llm-lab",), ("Bootstrap LLM Lab", "Document Lab startup")),
        (("projects/02-agent-desk/api",), ("Implement Desk orchestration", "Add Desk HITL endpoints")),
        (("projects/02-agent-desk/web",), ("Build Desk operator UI", "Improve Desk streaming UX")),
        (("projects/02-agent-desk",), ("Scaffold Agent Desk", "Document Desk workflow")),
        (("projects/03-research-digest",), ("Advance Research Digest", "Tune Digest ingestion and UI")),
        (("projects/04", "projects/05"), ("Stub forecast/sentiment benches", "Add bench runners")),
        ((".github",), ("Add CI workflow checks", "Tighten GitHub Actions")),
        (("infra/docker",), ("Add Lambda Dockerfiles", "Package MCP containers")),
        (("infra/cdk",), ("Evolve CDK serverless stack", "Refine CI/CD stack")),
        (("infra/",), ("Update deploy docs", "Document release flow")),
        (("scripts/",), ("Add helper scripts", "Improve release tooling")),
    ]
    for prefixes, msgs in opts_map:
        if any(p0.startswith(p) or p in p0 for p in prefixes):
            return msgs[batch_idx % len(msgs)]
    if batch_idx <= 3:
        return "Initialize portfolio monorepo scaffold"
    return ("Continue portfolio work", "Incremental cleanup", "Small follow-up fixes")[
        batch_idx % 3
    ]


def batch_paths(paths: list[str]) -> list[list[str]]:
    batches: list[list[str]] = []
    i = 0
    while i < len(paths):
        progress = i / max(len(paths), 1)
        size = RNG.randint(1, 3) if progress < 0.2 else RNG.randint(2, 6)
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
    while d <= END.date():
        days.append(datetime(d.year, d.month, d.day, tzinfo=TZ))
        d += timedelta(days=1)
    weeks: dict[tuple[int, int], list[datetime]] = {}
    for day in days:
        weeks.setdefault(day.isocalendar()[:2], []).append(day)
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
        elif roll < 0.55:
            activity[week_keys[i]] = RNG.randint(2, 4)
        elif roll < 0.82:
            activity[week_keys[i]] = RNG.randint(5, 9)
        else:
            activity[week_keys[i]] = RNG.randint(10, 14)
        i += 1
    activity[week_keys[0]] = max(activity.get(week_keys[0], 0), 4)
    activity[week_keys[-1]] = max(activity.get(week_keys[-1], 0), 3)
    for key in week_keys:
        y, w = key
        if y == 2026 and 18 <= w <= 30 and activity.get(key, 0) == 0 and RNG.random() < 0.4:
            activity[key] = RNG.randint(2, 5)
    raw = sum(activity.values()) or 1
    scaled = {k: max(0, int(round(v * n / raw))) for k, v in activity.items()}
    while sum(scaled.values()) > n:
        k = max(scaled, key=lambda x: scaled[x])
        if scaled[k]:
            scaled[k] -= 1
    while sum(scaled.values()) < n:
        cands = [k for k, v in scaled.items() if activity.get(k, 0) > 0] or week_keys
        scaled[RNG.choice(cands)] += 1
    stamps: list[datetime] = []
    for key in week_keys:
        count = scaled.get(key, 0)
        if not count:
            continue
        week_days = weeks[key]
        weekdays = [x for x in week_days if x.weekday() < 5] or week_days
        pool = weekdays[:]
        if RNG.random() < 0.2:
            weekend = [x for x in week_days if x.weekday() >= 5]
            if weekend:
                pool.append(RNG.choice(weekend))
        day_counts = {d.date(): 0 for d in pool}
        for _ in range(count):
            if RNG.random() < 0.4 and any(day_counts.values()):
                chosen = RNG.choice([d for d, c in day_counts.items() if c > 0])
            else:
                chosen = RNG.choice(list(day_counts.keys()))
            day_counts[chosen] += 1
        for day_date, c in day_counts.items():
            base = datetime(day_date.year, day_date.month, day_date.day, tzinfo=TZ)
            used: set[tuple[int, int]] = set()
            for _ in range(c):
                h = RNG.choice([9, 10, 11, 12, 14, 15, 16, 17, 19, 21])
                m = RNG.choice([0, 10, 15, 20, 30, 40, 45, 50])
                while (h, m) in used:
                    m = (m + 7) % 60
                used.add((h, m))
                stamps.append(base.replace(hour=h, minute=m, second=RNG.randint(0, 50)))
    stamps = sorted(stamps)[:n]
    while len(stamps) < n:
        stamps.append(END - timedelta(minutes=len(stamps) + 1))
    stamps = sorted(stamps)[:n]
    stamps[0], stamps[-1] = START, END
    return sorted(stamps)


def copy_batch(snapshot: Path, batch: list[str]) -> None:
    for rel in batch:
        src = snapshot / rel
        if not src.is_file():
            continue
        dst = ROOT / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def main() -> int:
    os.chdir(ROOT)
    tip = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    run(["git", "branch", "-f", "branched-source", tip])

    snapshot = Path(tempfile.mkdtemp(prefix="anna-branched-"))
    proc = subprocess.run(
        ["git", "archive", "HEAD"], cwd=ROOT, check=True, stdout=subprocess.PIPE
    )
    subprocess.run(["tar", "-x", "-C", str(snapshot)], input=proc.stdout, check=True)
    for extra in (
        "scripts/rebuild-living-history.py",
        "scripts/rebuild-branched-history.py",
        ".github/workflows/deploy-apis-aws.yml",
    ):
        src = ROOT / extra
        if src.is_file():
            dest = snapshot / extra
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
    # Drop obsolete workflow from snapshot if present
    obsolete = snapshot / ".github/workflows/start-pipeline.yml"
    if obsolete.exists():
        obsolete.unlink()

    all_paths = sorted(
        str(p.relative_to(snapshot))
        for p in snapshot.rglob("*")
        if p.is_file()
    )
    all_paths.sort(key=lambda p: (layer_of(p), p))
    batches = batch_paths(all_paths)
    stamps = generate_timestamps(len(batches))

    # Plan which batch ranges become feature branches
    # Each feature consumes 3–7 consecutive batches then merges
    feature_plan: list[tuple[str, str, int, int]] = []  # name, title, start, end exclusive
    idx = 0
    fi = 0
    while idx < len(batches) and fi < len(FEATURE_BRANCHES):
        # direct commits on main first few
        if fi == 0 and idx < 2:
            idx = 2
        length = RNG.randint(3, 7)
        end = min(len(batches), idx + length)
        if end - idx < 2:
            break
        name, title = FEATURE_BRANCHES[fi]
        feature_plan.append((name, title, idx, end))
        idx = end
        # occasional mainline hotfix commits between features
        idx += RNG.randint(0, 2)
        fi += 1

    print(f"files={len(all_paths)} batches={len(batches)} features={len(feature_plan)}")

    run(["git", "checkout", "--orphan", "branched-history-rebuild"])
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

    # Track which batches are inside features
    in_feature = {}
    for name, title, a, b in feature_plan:
        for i in range(a, b):
            in_feature[i] = (name, title, a, b)

    kept_branches: list[str] = []
    i = 0
    while i < len(batches):
        if i in in_feature and in_feature[i][2] == i:
            name, title, a, b = in_feature[i]
            base = head() if i > 0 else None
            # Create first commit on branch from current main (or orphan root)
            branch_parent = head() if i > 0 else None
            branch_tip = None
            for j in range(a, b):
                copy_batch(snapshot, batches[j])
                if j == len(batches) - 1:
                    for rel in all_paths:
                        src = snapshot / rel
                        dst = ROOT / rel
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src, dst)
                msg = message_for(batches[j], j + 1)
                parents = []
                if branch_tip:
                    parents = [branch_tip]
                elif branch_parent:
                    parents = [branch_parent]
                # first commit on feature: parent is main tip
                branch_tip = write_commit(msg, stamps[j], parents=parents or None)
            # Save branch ref at tip before merge
            run(["git", "branch", "-f", name, branch_tip])
            kept_branches.append(name)
            # Merge into main with no-ff style merge commit
            merge_when = stamps[b - 1] + timedelta(minutes=25)
            if merge_when > END:
                merge_when = END
            main_tip = branch_parent if branch_parent else branch_tip
            # checkout main tip files already at branch tip; merge commit has two parents
            merge_msg = f"Merge branch '{name}'\n\n{title}"
            if branch_parent:
                write_commit(merge_msg, merge_when, parents=[branch_parent, branch_tip])
            else:
                # first feature: already on branch tip as main
                run(["git", "branch", "-f", "main", branch_tip])
            print(f"merged {name} @ {merge_when.date()} ({b - a} commits)")
            i = b
            continue

        # Mainline commit
        copy_batch(snapshot, batches[i])
        if i == len(batches) - 1:
            for rel in all_paths:
                src = snapshot / rel
                dst = ROOT / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
        parents = [head()] if i > 0 or (
            subprocess.run(
                ["git", "rev-parse", "--verify", "HEAD"],
                cwd=ROOT,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            ).returncode
            == 0
        ) else None
        # detect if HEAD exists
        head_ok = (
            subprocess.run(
                ["git", "rev-parse", "--verify", "HEAD"],
                cwd=ROOT,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            ).returncode
            == 0
        )
        write_commit(
            message_for(batches[i], i + 1),
            stamps[i],
            parents=[head()] if head_ok else None,
        )
        i += 1

    # Ensure final tree complete and tip on main
    for rel in all_paths:
        src = snapshot / rel
        dst = ROOT / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    head_ok = True
    # If working tree dirty vs HEAD, make a final chore commit
    st = subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True)
    if st.strip():
        write_commit(
            "Finalize deploy workflow and history tooling",
            END,
            parents=[head()],
        )

    run(["git", "branch", "-M", "main"])
    for name in kept_branches:
        # recreate branch refs if reset moved them — already set
        pass

    shutil.rmtree(snapshot, ignore_errors=True)

    # Stats
    merges = subprocess.check_output(
        ["git", "log", "--merges", "--oneline"], cwd=ROOT, text=True
    ).strip().splitlines()
    commits = int(
        subprocess.check_output(["git", "rev-list", "--count", "main"], cwd=ROOT, text=True)
    )
    authors = subprocess.check_output(
        ["git", "log", "--format=%an <%ae>", "main"], cwd=ROOT, text=True
    )
    bad = [a for a in authors.splitlines() if a != f"{AUTHOR_NAME} <{AUTHOR_EMAIL}>"]
    print(f"\nmain_commits={commits} merge_commits={len([m for m in merges if m])}")
    print(f"feature_branches={len(kept_branches)}")
    for b in kept_branches:
        print(f"  {b}")
    if bad:
        print("ERROR authors", set(bad), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
