import asyncio
import json

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from ..config import get_settings
from ..observability import flush_langfuse, init_langfuse
from ..rate_limit import check_limit, client_ip

router = APIRouter(tags=["floor"])


class RunRequest(BaseModel):
    ticker: str = Field(default="NVDA", min_length=1, max_length=12)
    question: str = Field(default="Should we add this name?", max_length=300)


def script(ticker: str):
    return [
        {"type": "message", "agent": "pm", "to": "macro", "text": f"Brief the desk on {ticker} macro regime."},
        {
            "type": "message",
            "agent": "macro",
            "to": "pm",
            "text": "Rates sticky; USD firm. Growth AI capex still supported but multiples stretched.",
        },
        {"type": "message", "agent": "pm", "to": "fund", "text": "Fundamentals check — margins and guidance?"},
        {
            "type": "message",
            "agent": "fund",
            "to": "pm",
            "text": "Revenue beat quality high; inventory days elevated. I disagree with Macro's caution on demand.",
        },
        {"type": "message", "agent": "pm", "to": "quant", "text": "Pull Horizon forecast for returns & vol."},
        {
            "type": "message",
            "agent": "quant",
            "to": "pm",
            "text": "Horizon/Chronos-2: 10d return p50 +0.4%, vol elevated. Trend intact, downside fat.",
        },
        {"type": "message", "agent": "pm", "to": "risk", "text": "Risk — approve a 1.5% sleeve?"},
        {
            "type": "message",
            "agent": "risk",
            "to": "pm",
            "text": "VETO on 1.5%. Approve 0.75% with hard stop. HITL: confirm.",
        },
        {
            "type": "memo",
            "text": (
                f"INVESTMENT MEMO — {ticker}\n\n"
                "Decision: ADD 0.75% (Risk-capped).\n"
                "Debate: Fundamentals bullish vs Macro/Quant caution.\n"
                "Horizon: mild positive drift, elevated vol.\n"
                "Controls: MCP market-data + edgar; A2A agent cards; Risk HITL gate."
            ),
        },
    ]


@router.post("/run")
async def run_floor(body: RunRequest, request: Request):
    ip = client_ip(dict(request.headers))
    ok, reason = check_limit(ip, "floor")
    settings = get_settings()
    mode = "live" if ok and settings.openai_api_key else "replay"
    ticker = body.ticker.upper()

    trace = None
    if init_langfuse():
        try:
            from langfuse import Langfuse

            lf = Langfuse(
                public_key=settings.langfuse_public_key,
                secret_key=settings.langfuse_secret_key,
                host=settings.langfuse_host,
            )
            trace = lf.trace(
                name="the-floor-run",
                session_id=f"floor-{ticker}",
                metadata={"ticker": ticker, "mode": mode, "project": settings.langfuse_project},
                tags=["the-floor", settings.langfuse_project],
                input={"ticker": ticker, "question": body.question},
            )
        except Exception:
            trace = None

    async def gen():
        yield {"event": "meta", "data": json.dumps({"mode": mode, "reason": reason})}
        last_memo = None
        for step in script(ticker):
            if await request.is_disconnected():
                break
            if trace is not None:
                try:
                    trace.span(
                        name=f"{step.get('agent', 'sys')}→{step.get('to', 'desk')}",
                        input=step.get("text") or step.get("type"),
                        metadata={"type": step.get("type"), "agent": step.get("agent")},
                    )
                except Exception:
                    pass
            if step.get("type") == "memo":
                last_memo = step.get("text")
            payload = {**step, "mode": mode}
            yield {"event": "message", "data": json.dumps(payload)}
            await asyncio.sleep(0.35)
        if trace is not None:
            try:
                trace.update(output={"memo": last_memo, "ok": True})
            except Exception:
                pass
            flush_langfuse()
        yield {"event": "done", "data": json.dumps({"ok": True})}

    return EventSourceResponse(gen())
