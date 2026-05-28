"""Main orchestrator for multi-agent investment analysis."""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from .agents.macro import macro_agent
from .agents.quant import quant_agent
from .agents.research import research_agent
from .agents.risk import risk_agent
from .agents.scribe import scribe_agent
from .events import EventType, event_bus
from .hitl import approval_manager
from .llm import llm_client
from .models import ApprovalDecision, ApprovalRequest, RunRequest, RunState
from .usage import clear_usage, get_usage


SPECIALISTS = ("research", "macro", "quant")
MAX_PLAN_EDITS = 5
MAX_MEMO_EDITS = 5


class DeskOrchestrator:
    """Orchestrates multi-agent investment analysis with HITL approval gates."""

    def __init__(self) -> None:
        self.active_runs: Dict[str, RunState] = {}

    async def start_run(self, request: RunRequest) -> str:
        run_id = str(uuid.uuid4())
        run_state = RunState(
            id=run_id,
            ticker=request.ticker.upper(),
            question=request.question or "Provide a comprehensive investment analysis",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            started=False,
        )
        self.active_runs[run_id] = run_state
        clear_usage(run_id)
        # On Lambda, defer orchestration until the SSE stream connects so the
        # background work shares the same warm invocation as the stream.
        from .serverless_runtime import is_serverless, run_store

        if is_serverless():
            run_store.put(
                f"desk#{run_id}",
                "meta",
                {
                    "id": run_id,
                    "ticker": run_state.ticker,
                    "question": run_state.question,
                    "status": run_state.status,
                    "started": False,
                    "created_at": run_state.created_at.isoformat(),
                    "updated_at": run_state.updated_at.isoformat(),
                },
            )
        else:
            run_state.started = True
            asyncio.create_task(self._orchestrate_analysis(run_id, run_state))
        return run_id

    async def ensure_started(self, run_id: str) -> Optional[RunState]:
        """Start orchestration if this is the SSE invocation (serverless)."""
        run_state = self.get_run_state(run_id)
        if not run_state:
            return None
        if run_state.started:
            return run_state
        run_state.started = True
        run_state.updated_at = datetime.utcnow()
        from .serverless_runtime import run_store

        run_store.put(
            f"desk#{run_id}",
            "meta",
            {
                "id": run_id,
                "ticker": run_state.ticker,
                "question": run_state.question,
                "status": run_state.status,
                "started": True,
                "created_at": run_state.created_at.isoformat(),
                "updated_at": run_state.updated_at.isoformat(),
            },
        )
        asyncio.create_task(self._orchestrate_analysis(run_id, run_state))
        return run_state

    async def approve_gate(self, run_id: str, approval: ApprovalRequest) -> bool:
        from .serverless_runtime import is_serverless, run_store

        if is_serverless():
            run_store.put(
                f"desk#{run_id}",
                f"approval#{approval.tool_call_id}",
                {
                    "tool_call_id": approval.tool_call_id,
                    "decision": approval.decision.value
                    if hasattr(approval.decision, "value")
                    else str(approval.decision),
                    "message": approval.message,
                    "override_args": approval.override_args,
                },
            )
        if run_id not in self.active_runs:
            # Cross-invocation approve: DynamoDB write is enough for the
            # streaming instance to observe via polling.
            return is_serverless()
        return approval_manager.resolve_approval(approval.tool_call_id, approval)

    def get_run_state(self, run_id: str) -> Optional[RunState]:
        existing = self.active_runs.get(run_id)
        if existing:
            return existing
        from .serverless_runtime import is_serverless, run_store

        if not is_serverless():
            return None
        meta = run_store.get(f"desk#{run_id}", "meta")
        if not meta:
            return None
        run_state = RunState(
            id=meta["id"],
            ticker=meta["ticker"],
            question=meta.get("question") or "Provide a comprehensive investment analysis",
            status=meta.get("status") or "running",
            created_at=datetime.fromisoformat(meta["created_at"])
            if meta.get("created_at")
            else datetime.utcnow(),
            updated_at=datetime.fromisoformat(meta["updated_at"])
            if meta.get("updated_at")
            else datetime.utcnow(),
            started=bool(meta.get("started")),
        )
        self.active_runs[run_id] = run_state
        return run_state

    async def _orchestrate_analysis(self, run_id: str, run_state: RunState) -> None:
        ticker = run_state.ticker
        question = run_state.question
        user_feedback = ""

        try:
            await self._emit_agent_discoveries(run_id)

            # ── Plan gate loop (EDIT → replan with feedback) ──────────────
            selected: List[str] = list(SPECIALISTS)
            off_topic = False
            plan_edits = 0
            # Keep the user's original ask clean; feedback is passed separately.
            base_question = run_state.question

            while True:
                plan_data = await self._create_analysis_plan(
                    run_id,
                    ticker,
                    base_question,
                    user_feedback=user_feedback,
                    revision=plan_edits,
                )
                plan_md = plan_data["markdown"]
                selected = plan_data["agents"]
                off_topic = plan_data.get("off_topic", False)
                # Downstream agents use the revised objective (not raw feedback paste)
                question = plan_data.get("objective") or base_question

                run_state.status = "waiting_approval"
                plan_approval = await approval_manager.require_approval(
                    run_id=run_id,
                    gate_type="plan",
                    description=(
                        f"Revised analysis plan for {ticker}"
                        if plan_edits
                        else f"Analysis plan for {ticker}"
                    ),
                    content=plan_md,
                )

                if plan_approval.decision == ApprovalDecision.DENY:
                    await self._finish_run(run_id, "Plan rejected by user")
                    return

                if plan_approval.decision == ApprovalDecision.EDIT:
                    edit_note = (
                        (plan_approval.message or "").strip()
                        or json.dumps(plan_approval.override_args or {})
                    )
                    if not edit_note or edit_note in ("{}", "null"):
                        edit_note = "Please revise the analysis plan based on my preferences."
                    # Accumulate feedback notes only — never splice into Objective text
                    user_feedback = (
                        f"{user_feedback}\n{edit_note}".strip()
                        if user_feedback
                        else edit_note
                    )
                    plan_edits += 1
                    await event_bus.emit(
                        run_id,
                        EventType.MESSAGE_SENT,
                        "orchestrator",
                        {
                            "message": (
                                f"Rewriting plan from your feedback "
                                f"(attempt {plan_edits}/{MAX_PLAN_EDITS})"
                            )
                        },
                    )
                    if plan_edits >= MAX_PLAN_EDITS:
                        plan_data = await self._create_analysis_plan(
                            run_id,
                            ticker,
                            base_question,
                            user_feedback=user_feedback,
                            revision=plan_edits,
                        )
                        selected = plan_data["agents"]
                        off_topic = plan_data.get("off_topic", False)
                        question = plan_data.get("objective") or base_question
                        await event_bus.emit(
                            run_id,
                            EventType.MESSAGE_SENT,
                            "orchestrator",
                            {"message": "Max plan edits reached — proceeding with latest plan"},
                        )
                        break
                    continue

                # APPROVE — optionally fold approach into the working question
                approach = plan_data.get("approach") or []
                if approach:
                    bullets = "\n".join(f"- {b}" for b in approach)
                    question = (
                        f"{question}\n\nPlan focus (approved):\n{bullets}"
                    )
                break

            if off_topic and not selected:
                refusal = (
                    f"# Out of scope\n\n"
                    f"Agent Desk focuses on markets and investment analysis for public tickers. "
                    f"Your question about **{ticker}** appears outside that scope.\n\n"
                    f"Try asking about fundamentals, technicals, sector context, risk, or an investment memo."
                )
                run_state.final_memo = refusal
                memo_approval = await approval_manager.require_approval(
                    run_id=run_id,
                    gate_type="memo",
                    description=f"Desk response for {ticker}",
                    content=refusal,
                )
                if memo_approval.decision == ApprovalDecision.DENY:
                    await self._finish_run(run_id, "Response rejected by user")
                    return
                await self._finish_run(run_id, "Out-of-scope response delivered", refusal)
                return

            run_state.status = "running"
            await event_bus.emit(
                run_id,
                EventType.MESSAGE_SENT,
                "orchestrator",
                {"message": f"Starting agents: {', '.join(selected) or 'scribe only'}"},
            )

            research_result = ""
            macro_result = ""
            quant_result = ""
            risk_result = ""

            research_result, macro_result, quant_result = await self._run_specialists(
                run_id, ticker, question, selected
            )
            risk_result = await self._maybe_run_risk(
                run_id,
                ticker,
                question,
                research_result,
                macro_result,
                quant_result,
            )

            # ── Memo gate loop (EDIT → selective re-run + rewrite) ────────
            memo_edits = 0
            while True:
                await event_bus.emit(
                    run_id,
                    EventType.MESSAGE_SENT,
                    "orchestrator",
                    {"message": "Drafting final answer"},
                )
                memo_result = await self._run_agent_with_messages(
                    run_id,
                    "scribe",
                    scribe_agent.write_memo(
                        run_id,
                        ticker,
                        question,
                        research_result or "_not run_",
                        macro_result or "_not run_",
                        quant_result or "_not run_",
                        risk_result or "_not run_",
                        user_feedback=user_feedback,
                    ),
                )

                run_state.status = "waiting_approval"
                run_state.final_memo = memo_result
                memo_approval = await approval_manager.require_approval(
                    run_id=run_id,
                    gate_type="memo",
                    description=f"Investment memo for {ticker}",
                    content=memo_result,
                )

                if memo_approval.decision == ApprovalDecision.DENY:
                    await self._finish_run(run_id, "Memo rejected by user")
                    return

                if memo_approval.decision == ApprovalDecision.EDIT:
                    edit_note = (
                        (memo_approval.message or "").strip()
                        or json.dumps(memo_approval.override_args or {})
                    )
                    if not edit_note or edit_note in ("{}", "null"):
                        edit_note = "Please revise the memo based on my feedback."
                    user_feedback = (
                        f"{user_feedback}\nMemo edit request: {edit_note}".strip()
                        if user_feedback
                        else f"Memo edit request: {edit_note}"
                    )
                    memo_edits += 1

                    rerun = await self._agents_for_memo_edit(
                        run_id,
                        ticker,
                        question,
                        edit_note,
                        previously_run=selected,
                    )
                    await event_bus.emit(
                        run_id,
                        EventType.MESSAGE_SENT,
                        "orchestrator",
                        {
                            "message": (
                                f"Memo edit — re-running: "
                                f"{', '.join(rerun) or 'scribe only'} "
                                f"(attempt {memo_edits}/{MAX_MEMO_EDITS})"
                            )
                        },
                    )

                    run_state.status = "running"
                    if rerun:
                        r, m, q = await self._run_specialists(
                            run_id, ticker, question, rerun
                        )
                        if "research" in rerun:
                            research_result = r
                        if "macro" in rerun:
                            macro_result = m
                        if "quant" in rerun:
                            quant_result = q
                        risk_result = await self._maybe_run_risk(
                            run_id,
                            ticker,
                            question,
                            research_result,
                            macro_result,
                            quant_result,
                            force=True,
                        )

                    if memo_edits >= MAX_MEMO_EDITS:
                        # One last scribe pass then finish without another gate
                        memo_result = await self._run_agent_with_messages(
                            run_id,
                            "scribe",
                            scribe_agent.write_memo(
                                run_id,
                                ticker,
                                question,
                                research_result or "_not run_",
                                macro_result or "_not run_",
                                quant_result or "_not run_",
                                risk_result or "_not run_",
                                user_feedback=user_feedback,
                            ),
                        )
                        break
                    continue

                # APPROVE
                break

            run_state.final_memo = memo_result
            run_state.status = "completed"
            await self._finish_run(
                run_id, "Analysis completed successfully", memo_result
            )

        except Exception as e:
            print(f"Error in orchestration: {e}")
            await self._finish_run(run_id, f"Analysis failed: {e}")

    async def _run_specialists(
        self,
        run_id: str,
        ticker: str,
        question: str,
        selected: List[str],
    ) -> Tuple[str, str, str]:
        research_result = ""
        macro_result = ""
        quant_result = ""

        tasks = {}
        if "research" in selected:
            tasks["research"] = asyncio.create_task(
                self._run_agent_with_messages(
                    run_id,
                    "research",
                    research_agent.analyze_ticker(run_id, ticker, question),
                )
            )
        if "macro" in selected:
            tasks["macro"] = asyncio.create_task(
                self._run_agent_with_messages(
                    run_id,
                    "macro",
                    macro_agent.analyze_macro_context(run_id, ticker, question),
                )
            )
        if "quant" in selected:
            tasks["quant"] = asyncio.create_task(
                self._run_agent_with_messages(
                    run_id,
                    "quant",
                    quant_agent.analyze_quantitative(run_id, ticker, question),
                )
            )

        if not tasks:
            return research_result, macro_result, quant_result

        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        for name, result in zip(tasks.keys(), results):
            if isinstance(result, Exception):
                text = f"# {name.title()} failed\n\n`{result}`"
            else:
                text = result
            if name == "research":
                research_result = text
            elif name == "macro":
                macro_result = text
            elif name == "quant":
                quant_result = text
        return research_result, macro_result, quant_result

    async def _maybe_run_risk(
        self,
        run_id: str,
        ticker: str,
        question: str,
        research_result: str,
        macro_result: str,
        quant_result: str,
        force: bool = False,
    ) -> str:
        specialist_outputs = [research_result, macro_result, quant_result]
        if not force and not any(specialist_outputs):
            return ""
        if not any(specialist_outputs):
            return ""

        await event_bus.emit(
            run_id,
            EventType.MESSAGE_SENT,
            "orchestrator",
            {"message": "Starting risk assessment"},
        )
        return await self._run_agent_with_messages(
            run_id,
            "risk",
            risk_agent.assess_risk(
                run_id,
                ticker,
                research_result or "_not run_",
                macro_result or "_not run_",
                quant_result or "_not run_",
                question=question,
            ),
        )

    async def _agents_for_memo_edit(
        self,
        run_id: str,
        ticker: str,
        question: str,
        edit_note: str,
        previously_run: List[str],
    ) -> List[str]:
        """Decide which specialists to re-run for a memo edit request."""
        default = list(previously_run) or list(SPECIALISTS)
        if not llm_client.has_api_key():
            return default

        try:
            result = await llm_client.chat(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You decide which specialist agents must re-run after user memo feedback.\n"
                            "Agents: research (SEC/fundamentals), macro (sector/news), quant (prices/technicals).\n"
                            "Return ONLY JSON: "
                            '{"agents":["research"],"rationale":"..."}\n'
                            "Pick the minimal set needed to address the feedback. "
                            "Use [] only when the feedback is pure writing/style (scribe alone). "
                            "If unsure, re-run all previously used agents."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Ticker: {ticker}\n"
                            f"Question: {question}\n"
                            f"Previously run: {previously_run}\n"
                            f"User memo feedback: {edit_note}"
                        ),
                    },
                ],
                temperature=0.1,
                max_tokens=300,
                run_id=run_id,
                response_format={"type": "json_object"},
            )
            plan = json.loads(result["content"])
            agents = [
                a.lower()
                for a in (plan.get("agents") or [])
                if isinstance(a, str) and a.lower() in SPECIALISTS
            ]
            return agents
        except Exception:
            return default

    async def _emit_agent_discoveries(self, run_id: str) -> None:
        agents = [
            ("research", "Deep SEC filing analysis with hybrid RAG + Edgar"),
            ("macro", "Sector and economic analysis"),
            ("quant", "Technical and statistical analysis"),
            ("risk", "Integrated risk assessment"),
            ("scribe", "Investment memo synthesis"),
        ]
        for agent_name, description in agents:
            await event_bus.emit(
                run_id=run_id,
                event_type=EventType.AGENT_DISCOVERED,
                agent=agent_name,
                data={"description": description},
            )

    async def _create_analysis_plan(
        self,
        run_id: str,
        ticker: str,
        question: str,
        user_feedback: str = "",
        revision: int = 0,
    ) -> Dict[str, Any]:
        """LLM planner: rewrite a clean plan (agents + objective + approach)."""
        default = {
            "agents": list(SPECIALISTS),
            "off_topic": False,
            "objective": question,
            "approach": [
                "Fundamentals and competitive position (research)",
                "Sector / macro context (macro)",
                "Price action and risk metrics (quant)",
            ],
            "rationale": "Default full desk analysis",
            "changes_from_feedback": "",
        }

        if not llm_client.has_api_key():
            plan = dict(default)
            if user_feedback:
                lowered = user_feedback.lower()
                hinted = [a for a in SPECIALISTS if a in lowered]
                if hinted:
                    plan["agents"] = hinted
                # Lightweight rewrite without LLM
                plan["objective"] = (
                    f"{question.rstrip('.')}, incorporating: {user_feedback.strip()}"
                )
                plan["approach"] = [
                    f"Address user request: {user_feedback.strip()}",
                    *default["approach"],
                ]
                plan["rationale"] = (
                    "Plan revised from user feedback (heuristic mode — no LLM key)."
                )
                plan["changes_from_feedback"] = (
                    f"Updated objective and approach to cover: {user_feedback.strip()}"
                )
        else:
            try:
                feedback_instructions = (
                    (
                        "The user rejected the prior plan and asked for changes. "
                        "Produce a NEW plan that fully incorporates their feedback. "
                        "Rewrite objective and approach so the feedback is reflected as "
                        "concrete work the desk will do — do NOT paste the feedback verbatim "
                        "into the objective.\n"
                        f"User feedback:\n{user_feedback}\n"
                    )
                    if user_feedback
                    else ""
                )
                result = await llm_client.chat(
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are the orchestrator planner for an investment multi-agent desk.\n"
                                "Given a ticker and user question, produce a clear analysis plan.\n"
                                "Agents: research (SEC/fundamentals/valuation), macro (sector/news), "
                                "quant (prices/technicals). Risk and Scribe always run later if any "
                                "specialist runs.\n\n"
                                "Respond ONLY with JSON:\n"
                                "{\n"
                                '  "agents": ["research","macro","quant"],\n'
                                '  "off_topic": false,\n'
                                '  "objective": "1-2 sentence clean objective (no raw feedback quotes)",\n'
                                '  "approach": ["concrete workstream 1", "workstream 2", "..."],\n'
                                '  "rationale": "why these agents / this emphasis",\n'
                                '  "changes_from_feedback": "what changed vs prior plan, or empty string"\n'
                                "}\n"
                                "Use a subset for narrow questions (e.g. RSI → quant only). "
                                "Set off_topic=true and agents=[] for clearly non-finance questions.\n"
                                "When feedback asks to expand a topic (e.g. valuation), put that in "
                                "objective + approach and prefer agents that deliver it "
                                "(valuation → research; RSI → quant; sector → macro)."
                            ),
                        },
                        {
                            "role": "user",
                            "content": (
                                f"Ticker: {ticker}\n"
                                f"Original question: {question}\n"
                                f"{feedback_instructions}"
                            ),
                        },
                    ],
                    temperature=0.2,
                    max_tokens=700,
                    run_id=run_id,
                    response_format={"type": "json_object"},
                )
                plan = {**default, **json.loads(result["content"])}
            except Exception as e:
                plan = {**default, "rationale": f"Planner fallback ({e})"}

        agents = [
            a.lower()
            for a in (plan.get("agents") or [])
            if isinstance(a, str) and a.lower() in SPECIALISTS
        ]
        off_topic = bool(plan.get("off_topic"))
        if not off_topic and not agents:
            agents = list(SPECIALISTS)

        objective = (plan.get("objective") or question).strip()
        # Guard: never leave raw "User plan feedback" / "Plan edit:" dumps in objective
        if "user plan feedback" in objective.lower() or objective.lower().startswith(
            "plan edit:"
        ):
            objective = question

        approach_raw = plan.get("approach") or []
        if isinstance(approach_raw, str):
            approach = [approach_raw]
        else:
            approach = [str(a).strip() for a in approach_raw if str(a).strip()]

        rationale = (plan.get("rationale") or "Adaptive multi-agent plan").strip()
        changes = (plan.get("changes_from_feedback") or "").strip()
        if user_feedback and not changes:
            changes = "Plan updated to reflect your latest feedback."

        approach_md = (
            "\n".join(f"- {a}" for a in approach)
            if approach
            else "- Full multi-agent coverage"
        )
        agents_md = (
            "\n".join(f"- **{a}**" for a in agents)
            if agents
            else "- (none — scoped refusal)"
        )
        revision_banner = (
            f"\n> **Revision {revision}** — updated from your feedback\n"
            if revision and user_feedback
            else ""
        )
        changes_section = (
            f"\n## What changed\n{changes}\n" if changes and user_feedback else ""
        )

        markdown = f"""# Analysis Plan: {ticker}
{revision_banner}
## Objective
{objective}

## Approach
{approach_md}

## Scope
{"Out of desk scope (markets/finance only)" if off_topic else "In scope — live multi-agent analysis"}

## Agents selected
{agents_md}

## Always after specialists
- **risk** — if any specialist produces output
- **scribe** — final answer shaped to your question
{changes_section}
## Rationale
{rationale}

## Data sources
- Live Yahoo Finance (prices, info, news)
- Edgar SEC filings when available
- Local 10-K index cache for NVDA / AAPL / MSFT

## Approval gates
1. **Plan Gate** (this document)
2. **Memo Gate** — review final answer

Proceed with this plan?
"""
        return {
            "markdown": markdown,
            "agents": agents,
            "off_topic": off_topic,
            "rationale": rationale,
            "objective": objective,
            "approach": approach,
        }

    async def _run_agent_with_messages(
        self, run_id: str, agent_name: str, agent_coro
    ) -> str:
        await event_bus.emit(
            run_id=run_id,
            event_type=EventType.MESSAGE_SENT,
            agent="orchestrator",
            data={
                "to_agent": agent_name,
                "message_type": "task_assignment",
                "content": f"Starting {agent_name} analysis",
            },
        )
        result = await agent_coro
        await event_bus.emit(
            run_id=run_id,
            event_type=EventType.MESSAGE_RECEIVED,
            agent=agent_name,
            data={
                "from_agent": agent_name,
                "message_type": "analysis_result",
                "content": f"{agent_name.title()} analysis completed",
                "result_length": len(result) if isinstance(result, str) else 0,
            },
        )
        return result

    async def _finish_run(
        self, run_id: str, message: str, memo: Optional[str] = None
    ) -> None:
        if run_id in self.active_runs:
            run_state = self.active_runs[run_id]
            run_state.updated_at = datetime.utcnow()
            if memo:
                run_state.final_memo = memo
                run_state.status = "completed"
            else:
                run_state.status = "failed"

        # Emit usage before RUN_FINISHED — SSE clients close on run.finished
        usage = get_usage(run_id).as_event_data()
        await event_bus.emit(
            run_id=run_id,
            event_type=EventType.TOKEN_USAGE,
            data=usage,
        )

        await event_bus.emit(
            run_id=run_id,
            event_type=EventType.RUN_FINISHED,
            data={"message": message, "memo_available": memo is not None},
        )


orchestrator = DeskOrchestrator()
