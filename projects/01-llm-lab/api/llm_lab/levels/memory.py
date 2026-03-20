"""Level 1: Memory - Include conversation history."""

import time
from typing import List
from ..models import Turn, LevelOpts, LevelResult
from ..llm import llm_client
from ..replay import replay_system
from . import register_level


async def run(question: str, history: List[Turn], opts: LevelOpts) -> LevelResult:
    """
    Level 1: Memory - Include last 6 turns of conversation history.
    
    This level adds basic conversation memory to maintain context across turns.
    """
    start_time = time.time()
    
    # Take last 6 turns of history (last 3 exchanges)
    recent_history = history[-6:] if len(history) > 6 else history
    
    # Build messages with system prompt and conversation history
    messages = [
        {
            "role": "system",
            "content": "You are a helpful financial analysis assistant. Use the conversation history to provide contextual and relevant responses."
        }
    ]
    
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
    
    trace = {
        "level": "memory",
        "messages_count": len(messages),
        "history_turns_used": len(recent_history),
        "used_history": len(recent_history) > 0,
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
            level="memory",
            trace=trace
        )
        
    except RuntimeError as e:
        # Fallback to replay system
        if "no_key" in str(e):
            replay_result = await replay_system.get_replay_response("memory", question, len(recent_history))
            if replay_result:
                return replay_result
            
            return await replay_system.create_fallback_response(
                "memory", 
                question, 
                "OpenAI API key not configured"
            )
        else:
            return await replay_system.create_fallback_response(
                "memory", 
                question, 
                str(e)
            )


# Register this level
register_level(
    "memory",
    1,
    "Memory",
    "LLM with conversation history (last 6 turns)",
    "Added conversation memory for context continuity",
    run
)