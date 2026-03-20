"""Level 4: Smart RAG - Hybrid BM25 + dense retrieval with RRF."""

import time
import numpy as np
from typing import List
from ..models import Turn, LevelOpts, LevelResult, ChunkHit
from ..llm import llm_client
from ..replay import replay_system
from ..retrieval.store import data_store
from ..retrieval.bm25 import BM25
from ..retrieval.hybrid import HybridRetriever
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
    Level 4: Smart RAG - Hybrid BM25 + dense retrieval with RRF fusion.
    Falls back to Level 3 if BM25 index doesn't exist.
    """
    start_time = time.time()
    
    # Load indexed data
    chunks = data_store.load_chunks()
    embeddings = data_store.load_embeddings()
    bm25_data = data_store.load_bm25_index()
    
    if not chunks or embeddings is None:
        return await replay_system.create_fallback_response(
            "smart_rag",
            question,
            "No indexed data available - run indexer first"
        )
    
    trace = {
        "level": "smart_rag",
        "chunks_available": len(chunks),
        "embeddings_shape": embeddings.shape if embeddings is not None else None,
        "has_bm25_index": bm25_data is not None,
        "start_time": start_time,
        "steps": [],
        "retrieved_chunks": [],
        "prompt": None,
    }
    
    try:
        t0 = time.time()
        query_embedding = await llm_client.embed_single(question)
        append_step(trace["steps"], action="embed_query", detail={"dim": len(query_embedding)}, elapsed_seconds=time.time() - t0)
        
        t1 = time.time()
        if bm25_data is not None:
            # Use hybrid retrieval
            bm25_index = BM25.from_dict(bm25_data)
            hybrid_retriever = HybridRetriever(bm25_index, embeddings)
            
            # Perform hybrid search
            results, search_trace = await hybrid_retriever.search(
                question, query_embedding, top_k=30
            )
            
            # Take top 5 for context
            top_results = results[:5]
            
            # Build context from top chunks
            context_chunks = []
            chunk_hits = []
            retrieved = []
            
            for i, (chunk_idx, rrf_score, ranks) in enumerate(top_results):
                chunk = chunks[chunk_idx]
                context_chunks.append(f"[{i+1}] {chunk['text']}")
                
                chunk_hits.append(ChunkHit(
                    id=chunk['id'],
                    text=chunk['text'],
                    score=float(rrf_score),
                    source=chunk.get('source'),
                    ranks=ranks
                ))
                retrieved.append(serialize_chunk(chunk, score=float(rrf_score), rank=i + 1, extra={"ranks": ranks}))
            
            trace.update(search_trace)
            trace["retrieval_method"] = "hybrid_rrf"
            trace["rrf_scores"] = [float(score) for _, score, _ in top_results]
            append_step(
                trace["steps"],
                action="retrieve_hybrid_rrf",
                detail={**search_trace, "top_k": 5},
                elapsed_seconds=time.time() - t1,
            )
            
        else:
            # Fallback to naive cosine similarity (Level 3 behavior)
            similarities = []
            for i, chunk_embedding in enumerate(embeddings):
                similarity = cosine_similarity(query_embedding, chunk_embedding)
                similarities.append((i, similarity))
            
            similarities.sort(key=lambda x: x[1], reverse=True)
            top_results = similarities[:5]
            
            # Build context from top chunks
            context_chunks = []
            chunk_hits = []
            retrieved = []
            
            for i, (chunk_idx, score) in enumerate(top_results):
                chunk = chunks[chunk_idx]
                context_chunks.append(f"[{i+1}] {chunk['text']}")
                
                chunk_hits.append(ChunkHit(
                    id=chunk['id'],
                    text=chunk['text'],
                    score=float(score),
                    source=chunk.get('source')
                ))
                retrieved.append(serialize_chunk(chunk, score=float(score), rank=i + 1))
            
            trace.update({
                "retrieval_method": "cosine_similarity_fallback",
                "fallback_reason": "BM25 index not available",
                "cosine_scores": [float(score) for _, score in top_results]
            })
            append_step(
                trace["steps"],
                action="retrieve_cosine_fallback",
                detail={"reason": "no_bm25"},
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
        append_step(trace["steps"], action="generate_answer", elapsed_seconds=time.time() - t2)
        
        trace.update({
            "query_embedding_dim": len(query_embedding),
            "chunks_retrieved": len(chunk_hits),
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
            level="smart_rag",
            trace=trace
        )
        
    except RuntimeError as e:
        if "no_key" in str(e):
            replay_result = await replay_system.get_replay_response("smart_rag", question)
            if replay_result:
                return replay_result
            
            return await replay_system.create_fallback_response(
                "smart_rag", 
                question, 
                "OpenAI API key not configured"
            )
        else:
            return await replay_system.create_fallback_response(
                "smart_rag", 
                question, 
                str(e)
            )


# Register this level
register_level(
    "smart_rag",
    4,
    "Smart RAG",
    "Hybrid retrieval combining BM25 and dense vectors with RRF",
    "Added BM25 keyword search + dense vector fusion for better retrieval",
    run
)