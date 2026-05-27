"""Agent implementations for the desk."""

from .research import research_agent
from .macro import macro_agent
from .quant import quant_agent
from .risk import risk_agent
from .scribe import scribe_agent

__all__ = [
    "research_agent",
    "macro_agent",
    "quant_agent",
    "risk_agent",
    "scribe_agent",
]
