"""Level 5: Rerank RAG - Top-30 retrieval then LLM listwise reranking to top-5."""

import time
import numpy as np
from typing import List
from ..models import Turn, LevelOpts, LevelResult, ChunkHit
from ..llm import llm_client
from ..replay import replay_system
from ..retrieval.store import data_store
from ..retrieval.bm25 import BM25
from ..retrieval.hybrid import HybridRetriever
from ..retrieval.rerank import llm_listwise_rerank, score_based_rerank
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
    Level 5: Rerank RAG - Retrieve top-30 candidates, then use LLM to rerank to top-5.
    Falls back to score-based reranking if LLM reranking fails.
    """
    start_time = time.time()
    
    # Load indexed data
    chunks = data_store.load_chunks()
    embeddings = data_store.load_embeddings()
    bm25_data = data_store.load_bm25_index()
    
    if not chunks or embeddings is None:
        return await replay_system.create_fallback_response(
            "rerank_rag",
            question,
            "No indexed data available - run indexer first"
        )
    
    trace = {
        "level": "rerank_rag",
        "chunks_available": len(chunks),
        "embeddings_shape": embeddings.shape if embeddings is not None else None,
        "has_bm25_index": bm25_data is not None,
        "start_time": start_time,
        "steps": [],
        "retrieved_chunks": [],
        "candidate_chunks": [],
        "prompt": None,
    }
    
    try:
        # Get query embedding
        query_embedding = await llm_client.embed_single(question)
        
        # Phase 1: Initial retrieval (top-30)
        if bm25_data is not None:
            # Use hybrid retrieval
            bm25_index = BM25.from_dict(bm25_data)
            hybrid_retriever = HybridRetriever(bm25_index, embeddings)
            
            results, search_trace = await hybrid_retriever.search(
                question, query_embedding, top_k=30
            )
            
            # Extract top 30 candidates
            candidate_results = results[:30]
            initial_method = "hybrid_rrf"
            trace.update(search_trace)
            
        else:
            # Fallback to cosine similarity
            similarities = []
            for i, chunk_embedding in enumerate(embeddings):
                similarity = cosine_similarity(query_embedding, chunk_embedding)
                similarities.append((i, similarity))
            
            similarities.sort(key=lambda x: x[1], reverse=True)
            candidate_results = [(idx, score, {}) for idx, score in similarities[:30]]
            initial_method = "cosine_similarity_fallback"
            
        trace.update({
            "initial_retrieval_method": initial_method,
            "candidates_retrieved": len(candidate_results)
        })
        
        # Phase 2: LLM Reranking
        candidate_chunks = []
        candidate_scores = []
        
        for chunk_idx, score, ranks in candidate_results:
            candidate_chunks.append(chunks[chunk_idx])
            candidate_scores.append((chunk_idx, score))
        
        try:
            # Attempt LLM-based reranking
            rerank_start = time.time()
            reranked = await llm_listwise_rerank(question, candidate_chunks, top_k=5)
            rerank_elapsed = time.time() - rerank_start
            
            trace.update({
                "reranking_method": "llm_listwise",
                "reranking_elapsed_seconds": rerank_elapsed,
                "reranking_success": True
            })
            
        except Exception as e:
            # Fallback to score-based reranking
            reranked = score_based_rerank(candidate_scores, candidate_chunks, top_k=5)
            trace.update({
                "reranking_method": "score_based_fallback",
                "reranking_error": str(e),
                "reranking_success": False
            })
        
        # Build context from reranked results
        context_chunks = []
        chunk_hits = []
        retrieved = []
        candidates_preview = []
        
        for i, (c_idx, score, ranks) in enumerate(candidate_results[:10]):
            candidates_preview.append(
                serialize_chunk(chunks[c_idx], score=float(score), rank=i + 1, extra={"pre_rerank": True})
            )
        
        for i, (chunk_idx, relevance_score, explanation) in enumerate(reranked):
            chunk = candidate_chunks[chunk_idx]  # Index into candidates, not original chunks
            context_chunks.append(f"[{i+1}] {chunk['text']}")
            
            # Get original ranks if available
            original_ranks = {}
            if chunk_idx < len(candidate_results):
                original_ranks = candidate_results[chunk_idx][2]
            
            chunk_hits.append(ChunkHit(
                id=chunk['id'],
                text=chunk['text'],
                score=float(relevance_score),
                source=chunk.get('source'),
                ranks=original_ranks
            ))
            retrieved.append(
                serialize_chunk(
                    chunk,
                    score=float(relevance_score),
                    rank=i + 1,
                    extra={"explanation": explanation, "ranks": original_ranks},
                )
            )
        
        context = "\n\n".join(context_chunks)
        
        # Build prompt with retrieved and reranked context
        system_prompt = f"""You are a financial analysis assistant. Use the following retrieved and reranked context to answer the user's question accurately. The context has been specifically ranked for relevance to the query.

--- RERANKED CONTEXT ---
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
        result = await llm_client.chat(messages, temperature=0.2, max_tokens=600)
        
        trace.update({
            "query_embedding_dim": len(query_embedding),
            "chunks_retrieved": len(chunk_hits),
            "final_relevance_scores": [float(score) for _, score, _ in reranked],
            "retrieved_chunks": retrieved,
            "candidate_chunks": candidates_preview,
            "prompt": system_prompt,
            "messages": [{"role": m["role"], "content": m["content"][:500]} for m in messages],
            "llm_response": True,
            "usage": result["usage"],
            "elapsed_seconds": time.time() - start_time
        })
        append_step(trace["steps"], action="generate_answer", detail={"usage": result["usage"]})
        
        # Extract citations from chunk sources
        citations = [chunk.source for chunk in chunk_hits if chunk.source]
        citations = list(set(citations))  # Remove duplicates
        
        return LevelResult(
            answer=result["content"],
            citations=citations,
            level="rerank_rag",
            trace=trace
        )
        
    except RuntimeError as e:
        if "no_key" in str(e):
            replay_result = await replay_system.get_replay_response("rerank_rag", question)
            if replay_result:
                return replay_result
            
            return await replay_system.create_fallback_response(
                "rerank_rag", 
                question, 
                "OpenAI API key not configured"
            )
        else:
            return await replay_system.create_fallback_response(
                "rerank_rag", 
                question, 
                str(e)
            )


# Register this level
register_level(
    "rerank_rag",
    5,
    "Rerank RAG",
    "Two-stage retrieval with LLM-based reranking for precision",
    "Added LLM-based reranking of top candidates for better relevance",
    run
)