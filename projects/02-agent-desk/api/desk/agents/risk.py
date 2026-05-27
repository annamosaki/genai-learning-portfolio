"""Risk agent — LLM assessment over sibling agent outputs."""

from __future__ import annotations

from .base import BaseAgent


class RiskAgent(BaseAgent):
    name = "risk"
    description = "Risk assessment and portfolio impact analysis"

    async def assess_risk(
        self,
        run_id: str,
        ticker: str,
        research_analysis: str,
        macro_analysis: str,
        quant_analysis: str,
        question: str = "",
    ) -> str:
        system = (
            "You are the Risk Agent on an investment desk. "
            "Synthesize research, macro, and quant inputs into a detailed risk assessment "
            "with explanatory paragraphs (not only bullets). Include: overall risk rating "
            "(Low/Medium/High/Very High) with a 1-10 score, key risk themes with rationale, "
            "position sizing guidance, and a monitoring checklist. "
            "End with `## Sources` referencing which specialist findings drove each theme. "
            "Do not invent facts absent from inputs."
        )
        user = (
            f"Ticker: {ticker.upper()}\n"
            f"User question: {question or 'General risk assessment'}\n\n"
            f"## Research Agent Output\n{research_analysis[:10000]}\n\n"
            f"## Macro Agent Output\n{macro_analysis[:10000]}\n\n"
            f"## Quant Agent Output\n{quant_analysis[:10000]}\n\n"
            "Produce an integrated, detailed risk assessment with Sources."
        )
        return await self.run_llm_only(
            run_id=run_id,
            system_prompt=system,
            user_prompt=user,
            max_tokens=3500,
            task_label=f"Risk assessment for {ticker}",
        )


risk_agent = RiskAgent()
