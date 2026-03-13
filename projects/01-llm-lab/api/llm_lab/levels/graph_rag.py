"""Level 6: Graph RAG - Knowledge graph-based retrieval."""

import time
from typing import List
from ..models import Turn, LevelOpts, LevelResult
from ..llm import llm_client
from ..replay import replay_system
from ..retrieval.store import data_store
from ..graph.search import GraphSearcher
from . import register_level


async def run(question: str, history: List[Turn], opts: LevelOpts) -> LevelResult:
    """
    Level 6: Graph RAG - Use knowledge graph for entity and community-based retrieval.
    """
    start_time = time.time()
    
    # Load graph data
    graph_data = data_store.load_graph()
    communities_data = data_store.load_communities()
    
    if not graph_data or not communities_data:
        return await replay_system.create_fallback_response(
            "graph_rag",
            question,
            "Graph data not available - run indexer to build graph"
        )
    
    trace = {
        "level": "graph_rag",
        "graph_nodes": len(graph_data.get('nodes', [])),
        "graph_edges": len(graph_data.get('edges', [])),
        "communities_count": len(communities_data),
        "search_mode": opts.search_mode,
        "start_time": start_time,
        "steps": [],
        "retrieved_chunks": [],
        "prompt": None,
    }
    
    try:
        # Initialize graph searcher
        searcher = GraphSearcher(graph_data, communities_data)
        
        # Perform graph search based on mode
        t0 = time.time()
        graph_results, search_trace = searcher.combined_search(question, opts.search_mode)
        trace.update(search_trace)
        trace["steps"].append({
            "step": 1,
            "action": "graph_search",
            "status": "ok",
            "elapsed_seconds": time.time() - t0,
            "detail": {
                "mode": opts.search_mode,
                "results_count": len(graph_results),
                "types": [r.get("type") for r in graph_results[:20]],
            },
        })
        
        # Build context from graph results
        context_parts = []
        retrieved = []
        
        for i, result in enumerate(graph_results):
            if result['type'] == 'entity':
                text = (
                    f"Entity: {result['name']}\n"
                    f"Description: {result.get('description', 'N/A')}"
                )
            elif result['type'] == 'relation':
                text = (
                    f"Relationship: {result['source']} -> {result['relationship']} -> {result['target']}\n"
                    f"Description: {result.get('description', 'N/A')}"
                )
            elif result['type'] == 'community':
                text = (
                    f"Community: {result['title']}\n"
                    f"Summary: {result['summary']}\n"
                    f"Entities: {result['entities_count']} entities"
                )
            else:
                text = str(result)
            context_parts.append(text)
            retrieved.append({
                "id": f"graph-{i}",
                "text": text[:2500],
                "source": result.get("type"),
                "heading": result.get("name") or result.get("title") or result.get("type"),
                "rank": i + 1,
                "score": result.get("score"),
                "extra": {"graph_type": result.get("type")},
            })
        
        context = "\n\n".join(context_parts)
        
        # Build prompt with graph context
        system_prompt = f"""You are a financial analysis assistant with access to a knowledge graph of entities, relationships, and communities. Use the following graph context to answer the user's question.

--- GRAPH CONTEXT ---
{context}
--- END CONTEXT ---

Use the entity relationships and community information to provide a comprehensive answer. Reference specific entities and relationships when relevant."""

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
        t1 = time.time()
        result = await llm_client.chat(messages, temperature=0.2, max_tokens=600)
        trace["steps"].append({
            "step": 2,
            "action": "generate_answer",
            "status": "ok",
            "elapsed_seconds": time.time() - t1,
            "detail": {"usage": result["usage"], "answer_preview": result["content"][:300]},
        })
        
        # Extract citations from graph results
        citations = []
        for item in graph_results:
            if item['type'] == 'community':
                citations.append(f"Community: {item['title']}")
            elif item['type'] == 'entity':
                citations.append(f"Entity: {item['name']}")

        # Compact graph for inspector canvas
        nodes = graph_data.get("nodes", [])[:80]
        edges = graph_data.get("edges", [])[:120]
        
        trace.update({
            "context_items": len(graph_results),
            "context_length": len(context),
            "retrieved_chunks": retrieved,
            "prompt": system_prompt,
            "messages": [{"role": m["role"], "content": m["content"][:800]} for m in messages],
            "graph": {
                "nodes": [
                    {
                        "id": str(n.get("id", n.get("name", i))),
                        "label": n.get("name") or n.get("label") or str(n.get("id", i)),
                        "type": n.get("type"),
                    }
                    for i, n in enumerate(nodes)
                ],
                "edges": [
                    {
                        "from": str(e.get("source") or e.get("from")),
                        "to": str(e.get("target") or e.get("to")),
                        "label": e.get("relationship") or e.get("label"),
                    }
                    for e in edges
                    if (e.get("source") or e.get("from")) and (e.get("target") or e.get("to"))
                ],
            },
            "llm_response": True,
            "usage": result["usage"],
            "elapsed_seconds": time.time() - start_time
        })
        
        return LevelResult(
            answer=result["content"],
            citations=citations[:5],  # Limit citations
            level="graph_rag",
            trace=trace
        )
        
    except RuntimeError as e:
        if "no_key" in str(e):
            replay_result = await replay_system.get_replay_response("graph_rag", question)
            if replay_result:
                return replay_result
            
            return await replay_system.create_fallback_response(
                "graph_rag", 
                question, 
                "OpenAI API key not configured"
            )
        else:
            return await replay_system.create_fallback_response(
                "graph_rag", 
                question, 
                str(e)
            )


# Register this level
register_level(
    "graph_rag",
    6,
    "Graph RAG",
    "Knowledge graph-based retrieval with entities and communities",
    "Added graph-based retrieval using entity relationships and community summaries",
    run
)