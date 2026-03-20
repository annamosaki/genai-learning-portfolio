"""Level 0: Stateless - Single shot, no history."""

import time
from typing import List
from ..models import Turn, LevelOpts, LevelResult
from ..llm import llm_client
from ..replay import replay_system
from . import register_level


async def run(question: str, history: List[Turn], opts: LevelOpts) -> LevelResult:
    """
    Level 0: Stateless processing - single shot, no conversation history.
    
    This level demonstrates basic LLM interaction without any context or memory.
    """
    start_time = time.time()
    
    # Build prompt without any conversation history
    prompt = f"""You are a helpful financial analysis assistant. Answer the following question clearly and concisely.

Question: {question}

Please provide a focused answer based on your training data."""

    messages = [{"role": "user", "content": prompt}]
    
    trace = {
        "level": "stateless",
        "prompt": prompt,
        "messages_count": 1,
        "used_history": False,
        "start_time": start_time
    }
    
    try:
        # Attempt LLM call
        result = await llm_client.chat(messages, temperature=0.2, max_tokens=600)
        
        trace.update({
            "llm_response": True,
            "usage": result["usage"],
            "elapsed_seconds": time.time() - start_time
        })
        
        return LevelResult(
            answer=result["content"],
            citations=[],
            level="stateless",
            trace=trace
        )
        
    except RuntimeError as e:
        # Fallback to replay system
        if "no_key" in str(e):
            replay_result = await replay_system.get_replay_response("stateless", question)
            if replay_result:
                return replay_result
            
            return await replay_system.create_fallback_response(
                "stateless", 
                question, 
                "OpenAI API key not configured"
            )
        else:
            return await replay_system.create_fallback_response(
                "stateless", 
                question, 
                str(e)
            )


# Register this level
register_level(
    "stateless",
    0,
    "Stateless",
    "Basic LLM without conversation history or external knowledge",
    "Starting point - no context, no memory, pure LLM reasoning",
    run
)