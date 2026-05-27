"""Scribe agent — detailed, sourced investment memos."""

from __future__ import annotations

from datetime import datetime

from .base import BaseAgent


class ScribeAgent(BaseAgent):
    name = "scribe"
    description = "Investment memo writer synthesizing all agent analyses"

    async def write_memo(
        self,
        run_id: str,
        ticker: str,
        question: str,
        research_analysis: str,
        macro_analysis: str,
        quant_analysis: str,
        risk_analysis: str,
        user_feedback: str = "",
    ) -> str:
        system = (
            "You are the Scribe Agent on a professional multi-agent investment desk. "
            "Your job is to produce a thorough, readable research memo that a portfolio "
            "manager would actually use — not a short summary.\n\n"
            "## Output requirements\n"
            "- Use markdown with clear `##` / `###` section headings.\n"
            "- Default to a **long-form memo** (roughly 1,200–2,500 words) unless the user "
            "asked a narrowly factual question (e.g. a single RSI number). Even then, "
            "include methodology, context, and caveats — not one-liners.\n"
            "- Write in full paragraphs with explanation. Do not rely only on bullet lists; "
            "use bullets to support narrative, not replace it.\n"
            "- Never invent numbers, filings, headlines, or prices absent from the specialist "
            "inputs. If data is missing or degraded, say so explicitly and explain impact.\n"
            "- Include a brief disclaimer that this is AI-assisted research, not personalized advice.\n"
            "- If clearly off-topic for markets/finance, refuse politely.\n\n"
            "## Required structure for broad / investment questions\n"
            "1. `# Title` with company + ticker\n"
            "2. `## Executive summary` — 1–2 dense paragraphs + clear recommendation "
            "(BUY / HOLD / SELL / WATCH) with conviction and horizon\n"
            "3. `## Investment thesis` — multi-paragraph argument with key drivers\n"
            "4. `## Company & business context` — what the company does, segment mix if known\n"
            "5. `## Fundamental analysis` — cite Research agent findings; quote or paraphrase "
            "filing insights with attribution\n"
            "6. `## Macro & sector backdrop` — cite Macro agent; peers, news, sector dynamics\n"
            "7. `## Technical & quantitative picture` — cite Quant metrics with interpretation "
            "(what RSI/SMA/vol/drawdown imply for positioning)\n"
            "8. `## Risk assessment` — cite Risk agent score/themes; position sizing view\n"
            "9. `## Valuation & scenarios` — base / upside / downside narrative (only with "
            "available inputs; no fabricated targets)\n"
            "10. `## Catalysts & monitoring checklist`\n"
            "11. `## Sources & evidence` — REQUIRED. Numbered list of concrete sources drawn "
            "from specialist outputs, e.g.:\n"
            "    - `[R1]` Research / SEC / RAG excerpts (name the filing or tool if present)\n"
            "    - `[M1]` Macro / Yahoo Finance info or news headlines used\n"
            "    - `[Q1]` Quant metrics (price period, RSI, SMA, vol, etc.)\n"
            "    - `[K1]` Risk conclusions\n"
            "    Inline-cite these tags in the body where claims are made "
            "(e.g. \"Revenue momentum remains strong [R1]\").\n"
            "12. `## Conclusion`\n\n"
            "## Narrow questions\n"
            "Lead with a direct answer, then add: data used, interpretation, related risks, "
            "and a `## Sources & evidence` section. Still aim for substantial explanation "
            "(several paragraphs), not a tweet-length reply.\n"
        )
        feedback_block = (
            f"\n## User feedback on plan/memo\n{user_feedback}\n" if user_feedback else ""
        )
        # Pass generous specialist context so the scribe can cite details
        user = (
            f"Date: {datetime.utcnow().strftime('%B %d, %Y')}\n"
            f"Ticker: {ticker.upper()}\n"
            f"Question: {question}\n"
            f"{feedback_block}\n"
            "Synthesize the specialist reports below into the final memo. "
            "Preserve specific numbers, tool results, headlines, and filing references "
            "as citable evidence in `## Sources & evidence`.\n\n"
            f"## Research Agent report\n{research_analysis[:12000]}\n\n"
            f"## Macro Agent report\n{macro_analysis[:12000]}\n\n"
            f"## Quant Agent report\n{quant_analysis[:12000]}\n\n"
            f"## Risk Agent report\n{risk_analysis[:12000]}\n\n"
            "Write the full desk memo now."
        )
        return await self.run_llm_only(
            run_id=run_id,
            system_prompt=system,
            user_prompt=user,
            temperature=0.35,
            max_tokens=8000,
            task_label=f"Investment memo for {ticker}",
        )


scribe_agent = ScribeAgent()
