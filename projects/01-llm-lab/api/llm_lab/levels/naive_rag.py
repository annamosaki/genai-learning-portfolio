"""Level 3: Naive RAG - Simple cosine similarity retrieval."""

import time
import numpy as np
from typing import List
from ..models import Turn, LevelOpts, LevelResult, ChunkHit
from ..llm import llm_client
from ..replay import replay_system
from ..retrieval.store import data_store
from ..trace_util import serialize_chunk, append_step
from . import register_level


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Calculate cosine similarity between two vectors."""
    dot_product = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot_product / (norm_a * norm_b)


async def run(question: str, history: List[Turn], opts: LevelOpts) -> LevelResult:
    """
    Level 3: Naive RAG - Load chunks and embeddings, use cosine similarity for top-5 retrieval.
    """
    start_time = time.time()
    
    # Load indexed data
    chunks = data_store.load_chunks()
    embeddings = data_store.load_embeddings()
    
    if not chunks or embeddings is None:
        return await replay_system.create_fallback_response(
            "naive_rag",
            question,
            "No indexed data available - run indexer first"
        )
    
    trace = {
        "level": "naive_rag",
        "chunks_available": len(chunks),
        "embeddings_shape": embeddings.shape if embeddings is not None else None,
        "start_time": start_time,
        "steps": [],
        "retrieved_chunks": [],
        "prompt": None,
    }
    
    try:
        # Get query embedding
        t0 = time.time()
        query_embedding = await llm_client.embed_single(question)
        append_step(
            trace["steps"],
            action="embed_query",
            detail={"dim": len(query_embedding)},
            elapsed_seconds=time.time() - t0,
        )
        
        # Calculate similarities
        t1 = time.time()
        similarities = []
        for i, chunk_embedding in enumerate(embeddings):
            similarity = cosine_similarity(query_embedding, chunk_embedding)
            similarities.append((i, similarity))
        
        # Get top 5 chunks
        similarities.sort(key=lambda x: x[1], reverse=True)
        top_chunks = similarities[:5]
        
        # Build context from top chunks
        context_chunks = []
        chunk_hits = []
        retrieved = []
        
        for i, (chunk_idx, score) in enumerate(top_chunks):
            chunk = chunks[chunk_idx]
            context_chunks.append(f"[{i+1}] {chunk['text']}")
            
            chunk_hits.append(ChunkHit(
                id=chunk['id'],
                text=chunk['text'],
                score=float(score),
                source=chunk.get('source')
            ))
            retrieved.append(serialize_chunk(chunk, score=float(score), rank=i + 1))
        
        append_step(
            trace["steps"],
            action="retrieve_cosine",
            detail={"top_k": 5, "scores": [float(s) for _, s in top_chunks]},
            elapsed_seconds=time.time() - t1,
        )
        
        context = "\n\n".join(context_chunks)
        
        # Build prompt with retrieved context
        system_prompt = f"""You are a financial analysis assistant. Use the following retrieved context to answer the user's question accurately.

--- RETRIEVED CONTEXT ---
{context}
--- END CONTEXT ---

Cite the relevant sources ([1], [2], etc.) in your answer when using information from the context."""

        messages = [{"role": "system", "content": system_prompt}]
        
        # Add recent history (last 2 turns to save space)
        recent_history = history[-2:] if len(history) > 2 else history
        for turn in recent_history:
            messages.append({
                "role": turn.role,
                "content": turn.content
            })
        
        messages.append({
            "role": "user",
            "content": question
        })
        
        # Get LLM response
        t2 = time.time()
        result = await llm_client.chat(messages, temperature=0.2, max_tokens=600)
        append_step(
            trace["steps"],
            action="generate_answer",
            detail={"model": result.get("usage", {}).get("model")},
            elapsed_seconds=time.time() - t2,
        )
        
        trace.update({
            "retrieval_method": "cosine_similarity",
            "query_embedding_dim": len(query_embedding),
            "chunks_retrieved": len(chunk_hits),
            "top_scores": [float(score) for _, score in top_chunks],
            "retrieved_chunks": retrieved,
            "prompt": system_prompt,
            "messages": [{"role": m["role"], "content": m["content"][:500]} for m in messages],
            "llm_response": True,
            "usage": result["usage"],
            "elapsed_seconds": time.time() - start_time
        })
        
        # Extract citations from chunk sources
        citations = [chunk.source for chunk in chunk_hits if chunk.source]
        citations = list(set(citations))  # Remove duplicates
        
        return LevelResult(
            answer=result["content"],
            citations=citations,
            level="naive_rag",
            trace=trace
        )
        
    except RuntimeError as e:
        if "no_key" in str(e):
            replay_result = await replay_system.get_replay_response("naive_rag", question)
            if replay_result:
                return replay_result
            
            return await replay_system.create_fallback_response(
                "naive_rag", 
                question, 
                "OpenAI API key not configured"
            )
        else:
            return await replay_system.create_fallback_response(
                "naive_rag", 
                question, 
                str(e)
            )


# Register this level
register_level(
    "naive_rag",
    3,
    "Naive RAG",
    "Basic retrieval-augmented generation with cosine similarity",
    "Added document retrieval with vector similarity search",
    run
)