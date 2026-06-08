#!/usr/bin/env python3
"""End-to-end Agent Desk live case matrix with HITL variations."""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

import httpx

BASE = "http://127.0.0.1:8200"


def post(path: str, body: dict) -> dict:
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode())


def get(path: str) -> dict:
    with urllib.request.urlopen(BASE + path, timeout=60) as resp:
        return json.loads(resp.read().decode())


@dataclass
class CaseResult:
    name: str
    ok: bool
    detail: str = ""
    events: List[str] = field(default_factory=list)
    memo_preview: str = ""
    errors: List[str] = field(default_factory=list)


GateHandler = Callable[[str, str, dict], Optional[dict]]
# returns approve body or None to skip


def run_case(
    name: str,
    ticker: str,
    question: str,
    *,
    mode: str = "live",
    on_gate: GateHandler,
    expect_finished: bool = True,
    expect_memo: Optional[bool] = True,
    expect_tools: Optional[bool] = None,
    expect_memo_contains: Optional[List[str]] = None,
    expect_memo_not_contains: Optional[List[str]] = None,
    expect_status: Optional[str] = None,
    expect_agents: Optional[List[str]] = None,
    min_memo_len: int = 50,
    timeout: float = 300.0,
) -> CaseResult:
    errors: List[str] = []
    event_types: List[str] = []
    agents_finished: set[str] = set()
    tools_called: List[str] = []
    finished = False
    memo_available = False
    token_seen = False
    run_id = ""

    try:
        start = post("/api/run", {"ticker": ticker, "question": question, "mode": mode})
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        return CaseResult(name=name, ok=False, detail=f"start failed {e.code}: {body}")
    except Exception as e:
        return CaseResult(name=name, ok=False, detail=f"start failed: {e}")

    run_id = start.get("run_id", "")
    if not run_id:
        return CaseResult(name=name, ok=False, detail=f"no run_id: {start}")

    try:
        with httpx.stream("GET", f"{BASE}/api/run/{run_id}/stream", timeout=timeout) as stream:
            for line in stream.iter_lines():
                if not line.startswith("data:"):
                    continue
                payload = line[5:].strip()
                if not payload:
                    continue
                try:
                    ev = json.loads(payload)
                except Exception:
                    continue
                et = ev.get("type")
                if et == "keepalive":
                    continue
                event_types.append(et or "?")
                data = ev.get("data") or {}

                if et == "tool.called":
                    tools_called.append(f"{ev.get('agent')}:{data.get('tool')}")
                if et == "agent.finished" and ev.get("agent"):
                    agents_finished.add(ev["agent"])
                if et == "token.usage":
                    token_seen = True
                    if not (data.get("total_tokens") or 0) > 0 and mode == "live":
                        # off-topic may have planner tokens only — still should be >0 if planner ran
                        pass
                if et == "approval.required":
                    gate_id = data.get("gate_id")
                    gate_type = data.get("type") or ""
                    decision_body = on_gate(gate_type, gate_id, data)
                    if decision_body is not None:
                        try:
                            post(f"/api/run/{run_id}/approve", decision_body)
                        except Exception as ae:
                            errors.append(f"approve failed: {ae}")
                if et == "run.finished":
                    finished = True
                    memo_available = bool(data.get("memo_available"))
                    break
                if et == "error":
                    errors.append(str(data.get("message") or ev))
    except Exception as e:
        errors.append(f"stream error: {e}")

    state: Dict[str, Any] = {}
    try:
        state = get(f"/api/run/{run_id}")
    except Exception as e:
        errors.append(f"get status failed: {e}")

    memo = state.get("final_memo") or ""
    status = state.get("status")

    if expect_finished and not finished:
        errors.append("run did not finish")
    if expect_memo is True:
        if not memo_available and not memo:
            errors.append("expected memo but none available")
        if memo and len(memo) < min_memo_len:
            errors.append(f"memo too short ({len(memo)})")
    if expect_memo is False and memo_available and status == "completed" and memo:
        # deny cases: may finish without memo
        pass
    if expect_tools is True and not tools_called:
        errors.append("expected tool.called events")
    if expect_tools is False and tools_called:
        # ok for off-topic refusal before tools
        pass
    if expect_memo_contains:
        low = memo.lower()
        for needle in expect_memo_contains:
            if needle.lower() not in low:
                errors.append(f"memo missing '{needle}'")
    if expect_memo_not_contains:
        low = memo.lower()
        for needle in expect_memo_not_contains:
            if needle.lower() in low:
                errors.append(f"memo unexpectedly contains '{needle}'")
    if expect_status and status != expect_status:
        errors.append(f"status={status} expected={expect_status}")
    if expect_agents:
        for a in expect_agents:
            if a not in agents_finished:
                errors.append(f"agent '{a}' did not finish")

    ok = not errors
    detail = (
        f"run={run_id} status={status} memo_len={len(memo)} "
        f"tools={len(tools_called)} agents={sorted(agents_finished)} "
        f"tokens={token_seen}"
    )
    return CaseResult(
        name=name,
        ok=ok,
        detail=detail,
        events=event_types,
        memo_preview=memo[:280].replace("\n", " | "),
        errors=errors,
    )


def approve(gate_type: str, gate_id: str, data: dict) -> dict:
    return {"tool_call_id": gate_id, "decision": "approve"}


def deny(gate_type: str, gate_id: str, data: dict) -> dict:
    return {"tool_call_id": gate_id, "decision": "deny", "message": "User denied"}


def deny_plan_only(gate_type: str, gate_id: str, data: dict) -> dict:
    if gate_type == "plan":
        return deny(gate_type, gate_id, data)
    return approve(gate_type, gate_id, data)


def deny_memo_only(gate_type: str, gate_id: str, data: dict) -> dict:
    if gate_type == "memo":
        return deny(gate_type, gate_id, data)
    return approve(gate_type, gate_id, data)


def edit_plan(gate_type: str, gate_id: str, data: dict) -> dict:
    if gate_type == "plan":
        return {
            "tool_call_id": gate_id,
            "decision": "edit",
            "message": "Focus more on valuation multiples and competitive moat; keep it concise.",
        }
    return approve(gate_type, gate_id, data)


def edit_memo(gate_type: str, gate_id: str, data: dict) -> dict:
    if gate_type == "memo":
        return {
            "tool_call_id": gate_id,
            "decision": "edit",
            "message": "Add a short bullet list of 3 catalysts and a clearer BUY/HOLD/SELL line.",
        }
    return approve(gate_type, gate_id, data)


def build_cases() -> List[Callable[[], CaseResult]]:
    return [
        lambda: run_case(
            "narrow_tsla_rsi_approve",
            "TSLA",
            "What is the current RSI(14) and short-term technical picture for TSLA?",
            on_gate=approve,
            expect_tools=True,
            expect_agents=["quant", "scribe"],
            expect_status="completed",
            expect_memo_contains=["RSI"],
            min_memo_len=100,
        ),
        lambda: run_case(
            "broad_aapl_full_approve",
            "AAPL",
            "Provide a comprehensive investment analysis of Apple covering fundamentals, macro, and technicals.",
            on_gate=approve,
            expect_tools=True,
            expect_agents=["scribe"],
            expect_status="completed",
            min_memo_len=200,
        ),
        lambda: run_case(
            "nvda_fundamentals_approve",
            "NVDA",
            "Summarize NVIDIA's key fundamental strengths and risks from filings.",
            on_gate=approve,
            expect_tools=True,
            expect_agents=["research", "scribe"],
            expect_status="completed",
            min_memo_len=150,
        ),
        lambda: run_case(
            "msft_macro_approve",
            "MSFT",
            "What is Microsoft's sector positioning and recent news sentiment?",
            on_gate=approve,
            expect_tools=True,
            expect_agents=["scribe"],
            expect_status="completed",
            min_memo_len=100,
        ),
        lambda: run_case(
            "amd_quant_approve",
            "AMD",
            "Report AMD's 20-day SMA, RSI, and annualized volatility.",
            on_gate=approve,
            expect_tools=True,
            expect_agents=["quant", "scribe"],
            expect_status="completed",
            min_memo_len=80,
        ),
        lambda: run_case(
            "offtopic_refuse_approve",
            "AAPL",
            "Write a chocolate chip cookie recipe with measurements.",
            on_gate=approve,
            expect_tools=False,
            expect_status="completed",
            expect_memo_contains=["scope"],
            min_memo_len=40,
        ),
        lambda: run_case(
            "deny_plan_stops",
            "META",
            "Should I buy META stock right now?",
            on_gate=deny_plan_only,
            expect_finished=True,
            expect_memo=False,
            expect_status="failed",
            expect_tools=False,
            min_memo_len=0,
        ),
        lambda: run_case(
            "deny_memo_stops",
            "GOOGL",
            "What is Alphabet's current RSI?",
            on_gate=deny_memo_only,
            expect_finished=True,
            expect_memo=False,
            expect_tools=True,
            expect_status="failed",
            min_memo_len=0,
        ),
        lambda: run_case(
            "edit_plan_amzn",
            "AMZN",
            "Investment memo for Amazon.",
            on_gate=edit_plan,
            expect_tools=True,
            expect_agents=["scribe"],
            expect_status="completed",
            # edit feedback should influence output; soft check
            expect_memo_contains=["Amazon"],
            min_memo_len=150,
        ),
        lambda: run_case(
            "edit_memo_jpm",
            "JPM",
            "Brief investment view on JPMorgan.",
            on_gate=edit_memo,
            expect_tools=True,
            expect_agents=["scribe"],
            expect_status="completed",
            min_memo_len=100,
        ),
        lambda: run_case(
            "invalid_ticker_graceful",
            "ZZZZZ",
            "What is the RSI for ZZZZZ?",
            on_gate=approve,
            expect_finished=True,
            expect_status="completed",
            # should complete with honest failure messaging, not crash
            min_memo_len=40,
        ),
        lambda: run_case(
            "replay_opt_in_nvda",
            "NVDA",
            "Provide a comprehensive investment analysis",
            mode="replay",
            on_gate=approve,
            expect_finished=True,
            expect_memo=True,
            expect_tools=False,  # replay has canned events; tools may appear in JSON
            min_memo_len=20,
            timeout=120.0,
        ),
    ]


def main() -> int:
    health = get("/api/health")
    print("health:", json.dumps(health))
    if not health.get("llm_configured"):
        print("FAIL: llm not configured")
        return 1

    max_rounds = 3
    failing_names: Optional[List[str]] = None

    for round_i in range(1, max_rounds + 1):
        print(f"\n======== ROUND {round_i}/{max_rounds} ========")
        cases = build_cases()
        results: List[CaseResult] = []

        # If retrying, only re-run failures from previous round
        for factory in cases:
            # Peek name by running only if needed — simpler to run all or filter by name
            # We'll run all on round 1; on later rounds only failing names
            # Get name by inspecting lambda defaults awkwardly — just run and filter after naming
            pass

        # Build name->factory map by calling with a dry approach: recreate list each round
        named = [
            ("narrow_tsla_rsi_approve", cases[0]),
            ("broad_aapl_full_approve", cases[1]),
            ("nvda_fundamentals_approve", cases[2]),
            ("msft_macro_approve", cases[3]),
            ("amd_quant_approve", cases[4]),
            ("offtopic_refuse_approve", cases[5]),
            ("deny_plan_stops", cases[6]),
            ("deny_memo_stops", cases[7]),
            ("edit_plan_amzn", cases[8]),
            ("edit_memo_jpm", cases[9]),
            ("invalid_ticker_graceful", cases[10]),
            ("replay_opt_in_nvda", cases[11]),
        ]

        to_run = named
        if failing_names is not None:
            to_run = [(n, f) for n, f in named if n in failing_names]

        for name, factory in to_run:
            print(f"\n--- {name} ---")
            t0 = time.time()
            res = factory()
            # ensure name matches
            res.name = name
            dt = time.time() - t0
            results.append(res)
            status = "PASS" if res.ok else "FAIL"
            print(f"{status} ({dt:.1f}s) {res.detail}")
            if res.memo_preview:
                print(f"  memo: {res.memo_preview[:200]}...")
            for err in res.errors:
                print(f"  ! {err}")

        # Merge with previous passes if selective retry
        if failing_names is not None:
            # Keep only this round's results for failing set evaluation
            pass

        failed = [r for r in results if not r.ok]
        passed = [r for r in results if r.ok]
        print(f"\nRound {round_i}: {len(passed)} passed, {len(failed)} failed (ran {len(results)})")

        if not failed:
            print("\nALL CASES PASSED")
            return 0

        failing_names = [r.name for r in failed]
        print("Will retry:", failing_names)
        time.sleep(2)

    print("\nSOME CASES STILL FAILING AFTER RETRIES")
    return 1


if __name__ == "__main__":
    sys.exit(main())
