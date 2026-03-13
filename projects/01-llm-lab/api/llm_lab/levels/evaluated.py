"""Level 8: Evaluated RAG - Same as Level 5 but with evaluation note."""

import time
from typing import List
from ..models import Turn, LevelOpts, LevelResult
from . import register_level
from .rerank_rag import run as rerank_rag_run


async def run(question: str, history: List[Turn], opts: LevelOpts) -> LevelResult:
    """
    Level 8: Evaluated RAG - Same as Level 5 (rerank_rag) but with evaluation metadata.
    """
    start_time = time.time()
    
    # Run the underlying Level 5 (rerank_rag)
    result = await rerank_rag_run(question, history, opts)
    
    # Update the result with evaluation information
    result.level = "evaluated"
    result.trace["level"] = "evaluated"
    result.trace["base_level"] = "rerank_rag"
    result.trace["evaluation_available"] = True
    result.trace["evaluation_report"] = "data/index/eval-report.json"
    result.trace["evaluation_note"] = (
        "This level uses the same retrieval as rerank_rag but includes "
        "evaluation metrics for performance assessment. "
        "Check eval-report.json for detailed performance analysis."
    )
    result.trace["elapsed_seconds"] = time.time() - start_time
    
    return result


# Register this level
register_level(
    "evaluated",
    8,
    "Evaluated RAG", 
    "Performance-monitored RAG with evaluation metrics",
    "Added comprehensive evaluation framework with faithfulness and citation metrics",
    run
)