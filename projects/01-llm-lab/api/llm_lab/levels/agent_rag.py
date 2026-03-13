"""Level 9: Agent RAG - Agent with search_filings tool."""

import time
import json
from typing import List
from ..models import Turn, LevelOpts, LevelResult
from ..llm import llm_client
from ..replay import replay_system
from ..retrieval.store import data_store
from ..retrieval.hybrid import HybridRetriever
from ..retrieval.bm25 import BM25
from . import register_level


async def search_filings_tool(query: str, top_k: int = 5) -> dict:
    """
    Tool function for searching financial filings.
    Simulates what a pydantic-ai agent tool would do.
    """
    # Load indexed data
    chunks = data_store.load_chunks()
    embeddings = data_store.load_embeddings()
    bm25_data = data_store.load_bm25_index()
    
    if not chunks or embeddings is None:
        return {
            "results": [],
            "error": "No indexed filings available",
            "tool_used": "search_filings"
        }
    
    try:
        # Get query embedding
        query_embedding = await llm_client.embed_single(query)
        
        # Perform search
        if bm25_data:
            bm25_index = BM25.from_dict(bm25_data)
            hybrid_retriever = HybridRetriever(bm25_index, embeddings)
            results, _ = await hybrid_retriever.search(query, query_embedding, top_k=top_k)
            
            # Format results
            search_results = []
            for chunk_idx, score, ranks in results[:top_k]:
                chunk = chunks[chunk_idx]
                search_results.append({
                    "content": chunk["text"],
                    "source": chunk.get("source", "Unknown"),
                    "relevance_score": float(score),
                    "chunk_id": chunk["id"]
                })
        else:
            # Simple cosine similarity fallback
            similarities = []
            for i, chunk_embedding in enumerate(embeddings):
                dot_product = query_embedding.dot(chunk_embedding)
                norm_q = (query_embedding ** 2).sum() ** 0.5
                norm_c = (chunk_embedding ** 2).sum() ** 0.5
                similarity = dot_product / (norm_q * norm_c) if norm_q > 0 and norm_c > 0 else 0
                similarities.append((i, similarity))
            
            similarities.sort(key=lambda x: x[1], reverse=True)
            search_results = []
            for chunk_idx, score in similarities[:top_k]:
                chunk = chunks[chunk_idx]
                search_results.append({
                    "content": chunk["text"],
                    "source": chunk.get("source", "Unknown"), 
                    "relevance_score": float(score),
                    "chunk_id": chunk["id"]
                })
        
        return {
            "results": search_results,
            "tool_used": "search_filings",
            "query": query,
            "results_count": len(search_results)
        }
        
    except Exception as e:
        return {
            "results": [],
            "error": f"Search error: {str(e)}",
            "tool_used": "search_filings"
        }


async def run(question: str, history: List[Turn], opts: LevelOpts) -> LevelResult:
    """
    Level 9: Agent RAG - Multi-step agent with search_filings tool.
    
    Uses a simple multi-step approach:
    1. Search for relevant filings
    2. Use findings to answer the question
    """
    start_time = time.time()
    
    trace = {
        "level": "agent_rag",
        "agent_type": "simple_multi_step",
        "steps": [],
        "start_time": start_time
    }
    
    try:
        # Step 1: Search for relevant filings
        step1_start = time.time()
        search_results = await search_filings_tool(question, top_k=5)
        step1_time = time.time() - step1_start
        
        trace["steps"].append({
            "step": 1,
            "action": "search_filings",
            "status": "ok" if not search_results.get("error") else "error",
            "query": question,
            "results_count": len(search_results.get("results", [])),
            "elapsed_seconds": step1_time,
            "error": search_results.get("error"),
            "detail": {
                "results": [
                    {
                        "chunk_id": r.get("chunk_id"),
                        "source": r.get("source"),
                        "score": r.get("relevance_score"),
                        "text": (r.get("content") or "")[:800],
                    }
                    for r in search_results.get("results", [])
                ]
            },
        })
        
        # Format search results for context
        filing_context = ""
        citations = []
        retrieved = []
        
        if search_results.get("results"):
            context_parts = []
            for i, result in enumerate(search_results["results"]):
                context_parts.append(f"[{i+1}] {result['content']}")
                citations.append(result["source"])
                retrieved.append({
                    "id": result.get("chunk_id"),
                    "text": (result.get("content") or "")[:2500],
                    "source": result.get("source"),
                    "score": result.get("relevance_score"),
                    "rank": i + 1,
                })
            
            filing_context = "\n\n".join(context_parts)
        
        # Step 2: Generate answer using search results
        step2_start = time.time()
        
        system_prompt = f"""You are a financial analysis agent. You have searched for relevant information and found the following filing excerpts:

--- SEARCH RESULTS ---
{filing_context}
--- END RESULTS ---

Use this information to answer the user's question. Cite sources using [1], [2], etc. format."""

        messages = [{"role": "system", "content": system_prompt}]
        
        # Add recent history
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
        step2_time = time.time() - step2_start
        
        trace["steps"].append({
            "step": 2,
            "action": "generate_answer",
            "status": "ok",
            "context_length": len(filing_context),
            "elapsed_seconds": step2_time,
            "usage": result["usage"],
            "detail": {"answer_preview": result["content"][:300]},
        })
        
        trace.update({
            "total_steps": 2,
            "search_results_used": len(search_results.get("results", [])),
            "retrieved_chunks": retrieved,
            "prompt": system_prompt,
            "messages": [{"role": m["role"], "content": m["content"][:500]} for m in messages],
            "llm_response": True,
            "usage": result["usage"],
            "elapsed_seconds": time.time() - start_time
        })
        
        return LevelResult(
            answer=result["content"],
            citations=list(set(citations))[:5],  # Remove duplicates, limit to 5
            level="agent_rag",
            trace=trace
        )
        
    except RuntimeError as e:
        if "no_key" in str(e):
            replay_result = await replay_system.get_replay_response("agent_rag", question)
            if replay_result:
                return replay_result
            
            return await replay_system.create_fallback_response(
                "agent_rag", 
                question, 
                "OpenAI API key not configured"
            )
        else:
            return await replay_system.create_fallback_response(
                "agent_rag", 
                question, 
                str(e)
            )


# Register this level
register_level(
    "agent_rag",
    9,
    "Agent RAG",
    "Multi-step agent with search tool for dynamic retrieval",
    "Added agentic workflow with search_filings tool for dynamic information gathering",
    run
)