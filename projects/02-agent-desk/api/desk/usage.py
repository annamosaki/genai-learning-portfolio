"""Per-run token usage accumulator."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class UsageAccumulator:
    """Tracks prompt/completion tokens across LLM calls for a single run."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    calls: int = 0
    model: str = ""
    _extras: Dict[str, Any] = field(default_factory=dict)

    def add(self, usage: Dict[str, Any] | None) -> None:
        if not usage:
            return
        self.prompt_tokens += int(usage.get("prompt_tokens") or 0)
        self.completion_tokens += int(usage.get("completion_tokens") or 0)
        self.total_tokens += int(usage.get("total_tokens") or 0)
        self.calls += 1
        if usage.get("model"):
            self.model = str(usage["model"])

    def estimate_cost_usd(self) -> float:
        """Rough gpt-4o-mini estimate ($0.15 / 1M in, $0.60 / 1M out)."""
        return (self.prompt_tokens * 0.15 + self.completion_tokens * 0.60) / 1_000_000

    def as_event_data(self) -> Dict[str, Any]:
        return {
            "total_tokens": self.total_tokens,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "calls": self.calls,
            "model": self.model,
            "estimated_cost": round(self.estimate_cost_usd(), 6),
        }


# run_id -> accumulator
_usage_by_run: Dict[str, UsageAccumulator] = {}


def get_usage(run_id: str) -> UsageAccumulator:
    if run_id not in _usage_by_run:
        _usage_by_run[run_id] = UsageAccumulator()
    return _usage_by_run[run_id]


def clear_usage(run_id: str) -> None:
    _usage_by_run.pop(run_id, None)
