"""Level registry and implementations for LLM Lab."""

from typing import Dict, Callable, Awaitable, List
from ..models import Turn, LevelOpts, LevelResult, LevelInfo


# Level registry mapping level ID to metadata and run function
LEVELS: Dict[str, Dict] = {}


def register_level(
    level_id: str,
    number: int,
    title: str,
    blurb: str,
    what_changed: str,
    run_func: Callable[[str, List[Turn], LevelOpts], Awaitable[LevelResult]]
):
    """Register a level with its metadata and run function."""
    LEVELS[level_id] = {
        "id": level_id,
        "number": number,
        "title": title,
        "blurb": blurb,
        "what_changed": what_changed,
        "run": run_func
    }


def get_level_info() -> List[LevelInfo]:
    """Get list of all available levels with their metadata."""
    return [
        LevelInfo(
            id=level_data["id"],
            number=level_data["number"],
            title=level_data["title"],
            blurb=level_data["blurb"],
            what_changed=level_data["what_changed"]
        )
        for level_data in sorted(LEVELS.values(), key=lambda x: x["number"])
    ]


async def run_level(
    level_id: str,
    question: str,
    history: List[Turn],
    opts: LevelOpts
) -> LevelResult:
    """Run a specific level by ID. Accepts hyphen or underscore ids."""
    key = level_id.replace("-", "_")
    if key not in LEVELS:
        raise ValueError(f"Unknown level: {level_id}")
    
    run_func = LEVELS[key]["run"]
    return await run_func(question, history, opts)


# Import all level implementations to register them
from . import (
    stateless,
    memory,
    full_context,
    naive_rag,
    smart_rag,
    rerank_rag,
    graph_rag,
    secured,
    evaluated,
    agent_rag,
    agent_tools,
    agent_mcp
)