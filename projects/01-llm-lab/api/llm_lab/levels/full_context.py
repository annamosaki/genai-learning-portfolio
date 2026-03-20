"""Level 2: Full Context - Load first corpus file fully into prompt."""

import time
from pathlib import Path
from typing import List
from ..models import Turn, LevelOpts, LevelResult
from ..llm import llm_client
from ..replay import replay_system
from ..config import settings
from . import register_level


async def run(question: str, history: List[Turn], opts: LevelOpts) -> LevelResult:
    """
    Level 2: Full Context - Load the first corpus file completely into the prompt.
    
    This level demonstrates providing full document context rather than RAG chunks.
    """
    start_time = time.time()
    
    # Load first corpus file
    corpus_dir = Path(settings.corpus_dir)
    corpus_files = list(corpus_dir.glob("*.md"))
    
    full_context = ""
    corpus_file_used = None
    
    if corpus_files:
        # Use first corpus file
        corpus_file_used = str(corpus_files[0])
        try:
            with open(corpus_files[0], 'r') as f:
                full_context = f.read()
        except Exception as e:
            full_context = f"Error loading corpus file: {e}"
    
    # Take last 4 turns of history to save token space
    recent_history = history[-4:] if len(history) > 4 else history
    
    # Build system prompt with full document context
    system_prompt = f"""You are a financial analysis assistant. You have access to the following document for reference:

--- DOCUMENT CONTEXT ---
{full_context[:8000]}{'...' if len(full_context) > 8000 else ''}
--- END DOCUMENT CONTEXT ---

Use this document to answer questions accurately. Cite specific information when possible."""

    messages = [{"role": "system", "content": system_prompt}]
    
    # Add conversation history
    for turn in recent_history:
        messages.append({
            "role": turn.role,
            "content": turn.content
        })
    
    # Add current question
    messages.append({
        "role": "user",
        "content": question
    })
    
    doc_name = Path(corpus_file_used).name if corpus_file_used else None
    trace = {
        "level": "full_context",
        "corpus_file": corpus_file_used,
        "context_length": len(full_context),
        "context_truncated": len(full_context) > 8000,
        "messages_count": len(messages),
        "history_turns_used": len(recent_history),
        "start_time": start_time,
        "steps": [
            {
                "step": 1,
                "action": "load_document",
                "status": "ok" if full_context else "error",
                "detail": {
                    "file": doc_name,
                    "chars": len(full_context),
                    "truncated": len(full_context) > 8000,
                },
            }
        ],
        "retrieved_chunks": [
            {
                "id": doc_name or "full-doc",
                "text": full_context[:2500],
                "source": doc_name,
                "heading": "Full document (truncated for prompt)",
                "rank": 1,
                "size": len(full_context),
            }
        ] if full_context else [],
        "prompt": system_prompt,
        "messages": [{"role": m["role"], "content": m["content"][:800]} for m in messages],
    }
    
    try:
        # Attempt LLM call
        t0 = time.time()
        result = await llm_client.chat(messages, temperature=0.2, max_tokens=600)
        
        trace["steps"].append({
            "step": 2,
            "action": "generate_answer",
            "status": "ok",
            "elapsed_seconds": time.time() - t0,
            "detail": {"usage": result["usage"], "answer_preview": result["content"][:300]},
        })
        trace.update({
            "llm_response": True,
            "usage": result["usage"],
            "elapsed_seconds": time.time() - start_time
        })
        
        # Extract potential citations from the corpus file name
        citations = []
        if corpus_file_used:
            citations.append(Path(corpus_file_used).name)
        
        return LevelResult(
            answer=result["content"],
            citations=citations,
            level="full_context",
            trace=trace
        )
        
    except RuntimeError as e:
        # Fallback to replay system
        if "no_key" in str(e):
            replay_result = await replay_system.get_replay_response("full_context", question)
            if replay_result:
                return replay_result
            
            return await replay_system.create_fallback_response(
                "full_context", 
                question, 
                "OpenAI API key not configured"
            )
        else:
            return await replay_system.create_fallback_response(
                "full_context", 
                question, 
                str(e)
            )


# Register this level
register_level(
    "full_context",
    2,
    "Full Context",
    "LLM with complete document loaded in context",
    "Added full document context instead of chunked retrieval",
    run
)