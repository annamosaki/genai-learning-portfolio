#!/usr/bin/env python3
"""
Rebuild orphan git history with progressive milestones (2025-11-11 → 2026-08-11).
Author/committer: Anna Mosaki <mosakianna@gmail.com>
Run from repo root. Leaves branch `main` pointing at the new history;
previous tip saved as `legacy-codecommit`.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTHOR_NAME = "Anna Mosaki"
AUTHOR_EMAIL = "mosakianna@gmail.com"
TZ = timezone(timedelta(hours=1))  # Europe/Lisbon-ish fixed offset

# (relative_date_index is filled by spacing). Each step: (message, include_globs)
# Globs are matched against paths from git archive (posix).
# Later steps are cumulative: we always keep previously added files.

MILESTONES: list[tuple[str, list[str]]] = [
    (
        "Initialize monorepo scaffold and tooling",
        [
            ".gitignore",
            ".dockerignore",
            ".env.example",
            "README.md",
            "Makefile",
            "package.json",
            "package-lock.json",
            "Procfile",
            "start.sh",
        ],
    ),
    (
        "Add shared content model for CV and case studies",
        ["content/"],
    ),
    (
        "Add shared UI and eval packages",
        ["packages/"],
    ),
    (
        "Scaffold portfolio Next.js app shell",
        [
            "apps/web/package.json",
            "apps/web/tsconfig.json",
            "apps/web/next.config.ts",
            "apps/web/next-env.d.ts",
            "apps/web/postcss.config.mjs",
            "apps/web/tailwind.config.ts",
            "apps/web/app/globals.css",
            "apps/web/app/layout.tsx",
            "apps/web/app/page.tsx",
            "apps/web/app/favicon.ico",
        ],
    ),
    (
        "Build portfolio layout, header, and navigation",
        [
            "apps/web/components/",
            "apps/web/lib/",
            "apps/web/public/",
        ],
    ),
    (
        "Add portfolio pages for projects, writing, and about",
        [
            "apps/web/app/about/",
            "apps/web/app/projects/",
            "apps/web/app/writing/",
            "apps/web/app/opengraph-image.tsx",
            "apps/web/app/robots.ts",
            "apps/web/app/sitemap.ts",
        ],
    ),
    (
        "Add portfolio API service and health endpoints",
        ["services/api/"],
    ),
    (
        "Introduce LLM Lab project skeleton",
        [
            "projects/01-llm-lab/README.md",
            "projects/01-llm-lab/web/package.json",
            "projects/01-llm-lab/web/tsconfig.json",
            "projects/01-llm-lab/web/next.config.ts",
            "projects/01-llm-lab/web/next-env.d.ts",
            "projects/01-llm-lab/web/postcss.config.mjs",
            "projects/01-llm-lab/web/tailwind.config.ts",
            "projects/01-llm-lab/api/pyproject.toml",
            "projects/01-llm-lab/api/requirements.txt",
        ],
    ),
    (
        "Implement LLM Lab FastAPI chat and model routes",
        ["projects/01-llm-lab/api/"],
    ),
    (
        "Build LLM Lab web UI and zone base path",
        ["projects/01-llm-lab/web/"],
    ),
    (
        "Wire portfolio multi-zone rewrite for LLM Lab",
        [
            "apps/web/next.config.ts",
            "apps/web/components/zone-link.tsx",
            "apps/web/components/command-palette.tsx",
        ],
    ),
    (
        "Scaffold Agent Desk project structure",
        [
            "projects/02-agent-desk/README.md",
            "projects/02-agent-desk/web/package.json",
            "projects/02-agent-desk/web/tsconfig.json",
            "projects/02-agent-desk/web/next.config.ts",
            "projects/02-agent-desk/api/pyproject.toml",
            "projects/02-agent-desk/api/requirements.txt",
        ],
    ),
    (
        "Implement Agent Desk orchestration API and HITL flow",
        ["projects/02-agent-desk/api/"],
    ),
    (
        "Build Agent Desk operator UI",
        ["projects/02-agent-desk/web/"],
    ),
    (
        "Connect Agent Desk into portfolio demos zone",
        [
            "apps/web/next.config.ts",
            "apps/web/components/",
            "apps/web/app/status/",
        ],
    ),
    (
        "Scaffold Research Digest / Signal Desk",
        [
            "projects/03-research-digest/README.md",
            "projects/03-research-digest/web/package.json",
            "projects/03-research-digest/web/tsconfig.json",
            "projects/03-research-digest/web/next.config.ts",
            "projects/03-research-digest/api/pyproject.toml",
            "projects/03-research-digest/api/requirements.txt",
            "projects/03-research-digest/signal_desk/",
        ],
    ),
    (
        "Implement Research Digest API and ingestion sources",
        [
            "projects/03-research-digest/api/",
            "projects/03-research-digest/signal_desk/",
            "projects/03-research-digest/data/",
        ],
    ),
    (
        "Build Research Digest web experience",
        ["projects/03-research-digest/web/"],
    ),
    (
        "Add Research Digest to portfolio multi-zone routing",
        [
            "apps/web/next.config.ts",
            "apps/web/app/status/",
            "apps/web/components/",
        ],
    ),
    (
        "Add sentiment and forecast bench project stubs",
        [
            "projects/04-sentiment-bench/",
            "projects/05-forecast-bench/",
        ],
    ),
    (
        "Add GitHub Actions workflows for project CI checks",
        [
            ".github/",
            "projects/01-llm-lab/.github/",
            "projects/02-agent-desk/.github/",
            "infra/.github/",
        ],
    ),
    (
        "Add Cursor project rules for AWS workflows",
        [".cursor/"],
    ),
    (
        "Introduce serverless CDK app skeleton",
        [
            "infra/cdk/package.json",
            "infra/cdk/package-lock.json",
            "infra/cdk/cdk.json",
            "infra/cdk/tsconfig.json",
            "infra/cdk/bin/app.ts",
            "infra/DEPLOY.md",
        ],
    ),
    (
        "Define Lambda Docker images for portfolio APIs",
        [
            "infra/docker/",
            "infra/cdk/lib/portfolio-serverless-stack.ts",
        ],
    ),
    (
        "Wire Amplify hosting and CodeCommit source in CDK",
        [
            "infra/cdk/lib/portfolio-serverless-stack.ts",
            "infra/DEPLOY.md",
        ],
    ),
    (
        "Add serverless runtime helpers for Desk and Digest on Lambda",
        [
            "projects/02-agent-desk/api/",
            "projects/03-research-digest/api/",
        ],
    ),
    (
        "Adapt Lab and Desk clients for remote MCP endpoints",
        [
            "projects/01-llm-lab/api/",
            "projects/02-agent-desk/api/",
            "apps/web/app/status/",
        ],
    ),
    (
        "Package Yahoo Finance and Edgar MCP containers",
        [
            "infra/docker/Dockerfile.yf-mcp",
            "infra/docker/Dockerfile.edgar-mcp",
            "infra/cdk/lib/portfolio-serverless-stack.ts",
        ],
    ),
    (
        "Document custom domain layout for annamosaki.com",
        [
            "infra/DEPLOY.md",
            "apps/web/next.config.ts",
        ],
    ),
    (
        "Prefer custom API hostnames in CDK Amplify env",
        [
            "infra/cdk/lib/portfolio-serverless-stack.ts",
            "apps/web/next.config.ts",
        ],
    ),
    (
        "Add CodePipeline and CodeBuild for CDK API deploys",
        [
            "infra/cdk/lib/cicd-stack.ts",
            "infra/cdk/bin/app.ts",
            "infra/buildspec-cdk.yml",
            "infra/DEPLOY.md",
        ],
    ),
    (
        "Add push-deploy helper for one-command releases",
        [
            "scripts/push-deploy.sh",
            "infra/DEPLOY.md",
        ],
    ),
    (
        "Import OpenAI secret by name for safer CI deploys",
        [
            "infra/cdk/lib/portfolio-serverless-stack.ts",
        ],
    ),
    (
        "Use SUPERSEDED pipeline mode to avoid stacked deploys",
        [
            "infra/cdk/lib/cicd-stack.ts",
        ],
    ),
    (
        "Point everyday deploy flow at GitHub as source of truth",
        [
            "scripts/push-deploy.sh",
            "infra/DEPLOY.md",
            "README.md",
        ],
    ),
]


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=ROOT, check=True, text=True, **kwargs)


def match_paths(all_paths: list[str], patterns: list[str]) -> list[str]:
    out: list[str] = []
    for p in all_paths:
        for pat in patterns:
            if pat.endswith("/"):
                if p == pat[:-1] or p.startswith(pat):
                    out.append(p)
                    break
            elif p == pat:
                out.append(p)
                break
    return out


def date_sequence(n: int) -> list[datetime]:
    start = datetime(2025, 11, 11, 10, 30, tzinfo=TZ)
    end = datetime(2026, 8, 11, 11, 0, tzinfo=TZ)
    if n == 1:
        return [start]
    total = (end - start).total_seconds()
    dates: list[datetime] = []
    for i in range(n):
        t = start + timedelta(seconds=total * i / (n - 1))
        # Nudge to weekday daytime
        while t.weekday() >= 5:  # Sat/Sun → Monday
            t += timedelta(days=1)
        hour = 9 + (i * 3) % 8  # 9–16
        minute = 10 + (i * 7) % 45
        t = t.replace(hour=hour, minute=minute, second=0, microsecond=0)
        dates.append(t)
    dates[-1] = end
    return dates


def main() -> int:
    os.chdir(ROOT)

    # Snapshot current HEAD tree (tracked files only)
    snapshot = Path(tempfile.mkdtemp(prefix="anna-hist-"))
    proc = subprocess.run(
        ["git", "archive", "HEAD"],
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
    )
    subprocess.run(["tar", "-x", "-C", str(snapshot)], input=proc.stdout, check=True)

    all_paths = sorted(
        str(p.relative_to(snapshot))
        for p in snapshot.rglob("*")
        if p.is_file()
    )

    # Save legacy tip
    tip = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    branches = subprocess.check_output(["git", "branch", "--list", "legacy-codecommit"], cwd=ROOT, text=True)
    if "legacy-codecommit" not in branches:
        run(["git", "branch", "legacy-codecommit", tip])

    # Orphan rebuild
    run(["git", "checkout", "--orphan", "github-history-rebuild"])
    # Clear index and worktree tracked files
    run(["git", "rm", "-rf", "--ignore-unmatch", "."], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # Also clean untracked leftovers carefully — keep snapshot external
    for child in ROOT.iterdir():
        if child.name in {".git", ".venv", "node_modules", ".cursor"}:
            # keep .cursor? milestones include it later from snapshot
            if child.name == ".cursor":
                continue
            continue
        if child.name.startswith(".") and child.name not in {".gitignore", ".dockerignore", ".env.example", ".github"}:
            continue

    # Reset worktree to empty of previous content for paths we'll manage
    # Remove everything except .git and local env/venv
    keep = {".git", ".venv", "node_modules", ".env", ".env.local"}
    for child in list(ROOT.iterdir()):
        if child.name in keep:
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()

    included: set[str] = set()
    dates = date_sequence(len(MILESTONES))

    env_base = os.environ.copy()
    env_base.update(
        {
            "GIT_AUTHOR_NAME": AUTHOR_NAME,
            "GIT_AUTHOR_EMAIL": AUTHOR_EMAIL,
            "GIT_COMMITTER_NAME": AUTHOR_NAME,
            "GIT_COMMITTER_EMAIL": AUTHOR_EMAIL,
        }
    )

    for i, ((message, patterns), when) in enumerate(zip(MILESTONES, dates), start=1):
        paths = match_paths(all_paths, patterns)
        new_paths = [p for p in paths if p not in included]
        # Always allow re-copy of overlapping paths so updates land
        for rel in paths:
            src = snapshot / rel
            dst = ROOT / rel
            if not src.is_file():
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            included.add(rel)

        # Final milestone: ensure entire snapshot is present
        if i == len(MILESTONES):
            for rel in all_paths:
                src = snapshot / rel
                dst = ROOT / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                included.add(rel)

        run(["git", "add", "-A"])
        status = subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True)
        # Keep narrative milestones even when the tree did not change.
        allow_empty = not status.strip()

        iso = when.strftime("%Y-%m-%dT%H:%M:%S%z")
        env = env_base.copy()
        env["GIT_AUTHOR_DATE"] = iso
        env["GIT_COMMITTER_DATE"] = iso
        cmd = ["git", "commit", "-m", message]
        if allow_empty:
            cmd.insert(2, "--allow-empty")
        subprocess.run(cmd, cwd=ROOT, check=True, env=env)
        print(
            f"[{i:02d}/{len(MILESTONES)}] {iso} {message} "
            f"(+{len(new_paths)} new paths{', empty' if allow_empty else ''})"
        )

    # Replace main
    run(["git", "branch", "-M", "main"])
    shutil.rmtree(snapshot, ignore_errors=True)

    # Verify authors
    log = subprocess.check_output(
        ["git", "log", "--format=%an <%ae> | %cn <%ce> | %ad | %s", "--date=short"],
        cwd=ROOT,
        text=True,
    )
    print("\n--- history ---")
    print(log)
    bad = [line for line in log.splitlines() if "Anna Mosaki <mosakianna@gmail.com>" not in line]
    if bad:
        print("ERROR: non-Anna commits found:", file=sys.stderr)
        print("\n".join(bad), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
