"""Smoke benchmark writer + methodology stubs for purged walk-forward."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "content" / "artifacts" / "horizon"


def purged_folds(n: int, n_splits: int = 5, embargo: int = 5) -> list[tuple[np.ndarray, np.ndarray]]:
    """Lopez de Prado-style purged CV indices (simplified)."""
    fold_sizes = np.full(n_splits, n // n_splits)
    fold_sizes[: n % n_splits] += 1
    indices = np.arange(n)
    current = 0
    folds = []
    for fold_size in fold_sizes:
        start, stop = current, current + fold_size
        test = indices[start:stop]
        left = max(0, start - embargo)
        right = min(n, stop + embargo)
        train_mask = np.ones(n, dtype=bool)
        train_mask[left:right] = False
        train = indices[train_mask]
        folds.append((train, test))
        current = stop
    return folds


def smoke() -> None:
    rng = np.random.default_rng(42)
    returns = rng.normal(0, 0.01, 500)
    folds = purged_folds(len(returns))
    leaderboard = json.loads((OUT / "leaderboard.json").read_text()) if (OUT / "leaderboard.json").exists() else {
        "version": 1,
        "models": [],
    }
    leaderboard["folds"] = len(folds)
    leaderboard["contamination_note"] = (
        "Post-cutoff windows reported separately; TSFMs may have seen market data pre-cutoff."
    )
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "leaderboard.json").write_text(json.dumps(leaderboard, indent=2))
    if not (OUT / "sample-forecast.json").exists():
        raise SystemExit("sample-forecast.json missing — restore from content/artifacts")
    (OUT / "manifest.json").write_text(
        json.dumps(
            {
                "seed": 42,
                "mode": "smoke",
                "target": "log-returns + realised vol",
                "repro": "python -m horizon.run_benchmark --smoke",
            },
            indent=2,
        )
    )
    print(f"Horizon smoke OK — {len(folds)} purged folds")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    smoke()


if __name__ == "__main__":
    main()
