"""Main FastAPI application for Agent Desk."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette import EventSourceResponse

from .a2a_servers import a2a_manager
from .config import settings
from .events import event_bus, stream_events
from .llm import llm_client
from .models import ApprovalRequest, RunRequest, RunState
from .orchestrator import orchestrator

# Replay HITL: gate_id -> asyncio.Event set by /approve
_replay_gates: Dict[str, asyncio.Event] = {}
_replay_preapproved: set[str] = set()

app = FastAPI(
    title="Agent Desk API",
    description="Multi-agent investment analysis desk with live LLM agents",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "name": "Agent Desk API",
        "version": "2.0.0",
        "description": "Live multi-agent investment analysis",
        "llm_configured": llm_client.has_api_key(),
    }


@app.get("/health")
@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "ok": True,
        "agents": ["research", "macro", "quant", "risk", "scribe"],
        "a2a_enabled": settings.enable_a2a_servers,
        "llm_configured": llm_client.has_api_key(),
        "mode_default": "live",
    }


@app.post("/api/run")
async def start_run(request: RunRequest) -> Dict[str, str]:
    """Start a new investment analysis run (live by default)."""
    if not request.ticker or len(request.ticker) > 10:
        raise HTTPException(status_code=400, detail="Valid ticker symbol required")

    ticker = request.ticker.upper()
    mode = request.mode or "live"

    # Opt-in replay only
    if mode == "replay":
        if not settings.enable_replay:
            raise HTTPException(status_code=400, detail="Replay mode is disabled")
        replay_file = Path(settings.replay_dir) / "run-nvda.json"
        if ticker != "NVDA" or not replay_file.exists():
            raise HTTPException(
                status_code=400,
                detail="Replay mode currently supports ticker NVDA with an existing replay file",
            )
        return {
            "run_id": "replay-nvda-001",
            "status": "replay",
            "message": "Using opt-in replay data for NVDA",
        }

    if not llm_client.has_api_key():
        raise HTTPException(
            status_code=400,
            detail=(
                "OpenAI API key required for live analysis. "
                "Set OPENAI_API_KEY, or pass mode='replay' with ticker NVDA for the canned demo."
            ),
        )

    # Refresh client in case env loaded late
    if not llm_client.client:
        llm_client._setup_client()

    run_id = await orchestrator.start_run(request)
    return {
        "run_id": run_id,
        "status": "started",
        "message": "Analysis started with live agents",
    }


@app.get("/api/run/{run_id}/stream")
async def stream_run_events(run_id: str):
    if run_id == "replay-nvda-001":
        return EventSourceResponse(stream_replay_events(run_id))

    run_state = orchestrator.get_run_state(run_id)
    if not run_state:
        raise HTTPException(status_code=404, detail="Run not found")

    # Serverless: start orchestration inside the streaming invocation
    if not run_state.started:
        await orchestrator.ensure_started(run_id)

    return EventSourceResponse(stream_events(run_id, event_bus))


@app.post("/api/run/{run_id}/approve")
async def approve_gate(run_id: str, approval: ApprovalRequest) -> Dict[str, Any]:
    if run_id == "replay-nvda-001":
        gate_id = approval.tool_call_id
        evt = _replay_gates.get(gate_id)
        if evt:
            evt.set()
        else:
            _replay_preapproved.add(gate_id)
            for e in list(_replay_gates.values()):
                e.set()
        return {
            "status": "approved",
            "message": "Replay mode - approval recorded",
            "decision": approval.decision.value
            if hasattr(approval.decision, "value")
            else str(approval.decision),
        }

    run_state = orchestrator.get_run_state(run_id)
    if not run_state:
        raise HTTPException(status_code=404, detail="Run not found")

    success = await orchestrator.approve_gate(run_id, approval)
    if success:
        return {
            "status": "processed",
            "decision": approval.decision.value,
        }
    raise HTTPException(status_code=400, detail="Invalid approval gate")


@app.get("/api/run/{run_id}")
async def get_run_status(run_id: str) -> RunState:
    if run_id == "replay-nvda-001":
        return RunState(
            id=run_id,
            ticker="NVDA",
            question="Provide comprehensive investment analysis",
            status="completed",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            final_memo=(
                "# INVESTMENT MEMO: NVDA (Replay Mode)\n\n"
                "This is simulated replay data for demonstration purposes."
            ),
        )

    run_state = orchestrator.get_run_state(run_id)
    if not run_state:
        raise HTTPException(status_code=404, detail="Run not found")
    return run_state


@app.get("/api/agents")
async def list_agents() -> Dict[str, Any]:
    agents = {
        "research": {
            "name": "Research Agent",
            "description": "Deep analysis of SEC filings using GraphRAG and Edgar MCP",
            "capabilities": ["sec_filing_analysis", "graph_rag_search", "edgar_mcp"],
            "status": "active",
        },
        "macro": {
            "name": "Macro Agent",
            "description": "Sector and macroeconomic analysis via news and market data",
            "capabilities": ["sector_analysis", "news_sentiment", "live_yfinance"],
            "status": "active",
        },
        "quant": {
            "name": "Quantitative Agent",
            "description": "Technical analysis and quantitative metrics from live price data",
            "capabilities": ["technical_analysis", "risk_metrics", "price_patterns"],
            "status": "active",
        },
        "risk": {
            "name": "Risk Agent",
            "description": "Risk assessment from integrated multi-agent analysis",
            "capabilities": ["risk_assessment", "position_sizing", "portfolio_impact"],
            "status": "active",
        },
        "scribe": {
            "name": "Scribe Agent",
            "description": "Investment memo synthesis from all agent inputs",
            "capabilities": ["memo_writing", "investment_thesis", "synthesis"],
            "status": "active",
        },
    }
    return {
        "agents": agents,
        "total_count": len(agents),
        "a2a_enabled": settings.enable_a2a_servers,
        "llm_configured": llm_client.has_api_key(),
    }


@app.get("/api/agents/cards")
async def get_agent_cards() -> Dict[str, Any]:
    if settings.enable_a2a_servers:
        cards = a2a_manager.get_agent_cards()
    else:
        cards = {}
        agents_info = await list_agents()
        for agent_name, agent_info in agents_info["agents"].items():
            cards[agent_name] = {
                "name": f"{agent_name}_agent",
                "description": agent_info["description"],
                "capabilities": agent_info["capabilities"],
                "tools": [
                    {
                        "name": f"analyze_{agent_name}",
                        "description": f"Perform {agent_name} analysis",
                    }
                ],
                "endpoints": {"note": "In-process agent - A2A servers disabled"},
            }
    return {
        "cards": cards,
        "a2a_mode": "servers" if settings.enable_a2a_servers else "in_process",
    }


async def stream_replay_events(run_id: str):
    """Stream replay events from JSON file, pausing on approval.required."""
    replay_file = Path(settings.replay_dir) / "run-nvda.json"
    if not replay_file.exists():
        yield {"data": json.dumps({"type": "error", "message": "Replay file not found"})}
        return

    try:
        with open(replay_file, "r") as f:
            events = json.load(f)

        for event in events:
            yield {"data": json.dumps(event)}

            if event.get("type") == "approval.required":
                gate_id = (event.get("data") or {}).get("gate_id") or f"{run_id}_gate"
                if gate_id in _replay_preapproved:
                    _replay_preapproved.discard(gate_id)
                else:
                    evt = asyncio.Event()
                    _replay_gates[gate_id] = evt
                    try:
                        await asyncio.wait_for(evt.wait(), timeout=8)
                    except asyncio.TimeoutError:
                        yield {
                            "data": json.dumps(
                                {
                                    "type": "approval.resolved",
                                    "run_id": run_id,
                                    "data": {
                                        "gate_id": gate_id,
                                        "decision": "approve",
                                        "auto": True,
                                        "message": "Auto-approved after timeout (replay)",
                                    },
                                }
                            )
                        }
                    finally:
                        _replay_gates.pop(gate_id, None)

            await asyncio.sleep(0.12)

    except Exception as e:
        yield {"data": json.dumps({"type": "error", "message": str(e)})}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "desk.app:app",
        host=settings.host,
        port=settings.api_port,
        reload=settings.debug,
    )
