"""Level 10: Agent Tools - Multi-tool agent with compute_metric and list_documents."""

import time
import json
import re
from typing import List, Dict, Any
from ..models import Turn, LevelOpts, LevelResult
from ..llm import llm_client
from ..replay import replay_system
from ..retrieval.store import data_store
from .agent_rag import search_filings_tool
from . import register_level


async def compute_metric_tool(metric_name: str, company: str = "", year: str = "") -> dict:
    """
    Tool for computing financial metrics from figures.json.
    """
    try:
        figures_data = data_store.load_figures()
        
        if not figures_data:
            return {
                "result": None,
                "error": "No financial figures available",
                "tool_used": "compute_metric"
            }
        
        # Search for the metric
        metric_lower = metric_name.lower()
        company_lower = company.lower() if company else ""
        
        found_metrics = []
        
        for company_key, company_data in figures_data.items():
            if company_lower and company_lower not in company_key.lower():
                continue
                
            if isinstance(company_data, dict):
                for metric_key, metric_value in company_data.items():
                    if metric_lower in metric_key.lower():
                        found_metrics.append({
                            "company": company_key,
                            "metric": metric_key,
                            "value": metric_value,
                            "year": year or "latest"
                        })
        
        if found_metrics:
            return {
                "results": found_metrics,
                "tool_used": "compute_metric",
                "metric_searched": metric_name,
                "company_filter": company,
                "year_filter": year
            }
        else:
            return {
                "results": [],
                "message": f"No data found for metric '{metric_name}'" + (f" for company '{company}'" if company else ""),
                "tool_used": "compute_metric"
            }
            
    except Exception as e:
        return {
            "result": None,
            "error": f"Error computing metric: {str(e)}",
            "tool_used": "compute_metric"
        }


async def list_documents_tool(company: str = "") -> dict:
    """
    Tool for listing available documents.
    """
    try:
        chunks = data_store.load_chunks()
        
        if not chunks:
            return {
                "documents": [],
                "error": "No documents available",
                "tool_used": "list_documents"
            }
        
        # Extract unique document sources
        sources = set()
        for chunk in chunks:
            source = chunk.get("source", "Unknown")
            if company and company.lower() not in source.lower():
                continue
            sources.add(source)
        
        documents = list(sources)
        
        return {
            "documents": documents,
            "count": len(documents),
            "company_filter": company,
            "tool_used": "list_documents"
        }
        
    except Exception as e:
        return {
            "documents": [],
            "error": f"Error listing documents: {str(e)}",
            "tool_used": "list_documents"
        }


async def determine_tool_usage(question: str) -> List[str]:
    """
    Simple heuristic to determine which tools to use based on the question.
    """
    question_lower = question.lower()
    tools_to_use = []
    
    # Keywords that suggest metric computation
    metric_keywords = ["revenue", "profit", "earnings", "margin", "ratio", "calculate", "compute", "metric", "financial"]
    if any(keyword in question_lower for keyword in metric_keywords):
        tools_to_use.append("compute_metric")
    
    # Keywords that suggest document listing
    list_keywords = ["documents", "filings", "reports", "list", "available", "what documents", "which files"]
    if any(keyword in question_lower for keyword in list_keywords):
        tools_to_use.append("list_documents")
    
    # Always include search if no specific tools identified or if asking about content
    search_keywords = ["what", "how", "why", "when", "where", "explain", "describe", "tell me about"]
    if not tools_to_use or any(keyword in question_lower for keyword in search_keywords):
        tools_to_use.append("search_filings")
    
    return tools_to_use


async def run(question: str, history: List[Turn], opts: LevelOpts) -> LevelResult:
    """
    Level 10: Agent Tools - Multi-tool agent with compute_metric, list_documents, and search_filings.
    """
    start_time = time.time()
    
    trace = {
        "level": "agent_tools",
        "agent_type": "multi_tool",
        "tools_available": ["search_filings", "compute_metric", "list_documents"],
        "steps": [],
        "start_time": start_time
    }
    
    try:
        # Step 1: Determine which tools to use
        tools_to_use = await determine_tool_usage(question)
        trace["tools_selected"] = tools_to_use
        
        # Step 2: Execute tools
        tool_results = {}
        all_citations = []
        
        for tool_name in tools_to_use:
            tool_start = time.time()
            
            if tool_name == "search_filings":
                result = await search_filings_tool(question, top_k=5)
                if result.get("results"):
                    all_citations.extend([r["source"] for r in result["results"]])
            elif tool_name == "compute_metric":
                # Extract metric name and company from question
                metric_match = re.search(r'(revenue|profit|earnings|margin|ratio|sales)', question, re.IGNORECASE)
                company_match = re.search(r'(NVDA|AAPL|MSFT|NVIDIA|Apple|Microsoft)', question, re.IGNORECASE)
                
                metric_name = metric_match.group(0) if metric_match else "revenue"
                company_name = company_match.group(0) if company_match else ""
                
                result = await compute_metric_tool(metric_name, company_name)
            elif tool_name == "list_documents":
                company_match = re.search(r'(NVDA|AAPL|MSFT|NVIDIA|Apple|Microsoft)', question, re.IGNORECASE)
                company_name = company_match.group(0) if company_match else ""
                
                result = await list_documents_tool(company_name)
            else:
                result = {"error": f"Unknown tool: {tool_name}"}
            
            tool_time = time.time() - tool_start
            tool_results[tool_name] = result
            ok = "error" not in result or not result.get("error")
            
            trace["steps"].append({
                "step": len(trace["steps"]) + 1,
                "action": f"tool:{tool_name}",
                "tool": tool_name,
                "status": "ok" if ok else "error",
                "elapsed_seconds": tool_time,
                "success": ok,
                "detail": {
                    "error": result.get("error"),
                    "count": len(result.get("results", result.get("documents", [])) or []),
                    "preview": result.get("results", result.get("documents", []))[:3]
                    if isinstance(result.get("results") or result.get("documents"), list)
                    else result,
                },
            })
        
        # Step 3: Synthesize results into context
        context_parts = []
        retrieved = []
        
        if "search_filings" in tool_results:
            search_result = tool_results["search_filings"]
            if search_result.get("results"):
                context_parts.append("--- FILING SEARCH RESULTS ---")
                for i, result in enumerate(search_result["results"][:3]):
                    context_parts.append(f"[{i+1}] {result['content']}")
                    retrieved.append({
                        "id": result.get("chunk_id"),
                        "text": (result.get("content") or "")[:2500],
                        "source": result.get("source"),
                        "score": result.get("relevance_score"),
                        "rank": i + 1,
                    })
                context_parts.append("")
        
        if "compute_metric" in tool_results:
            metric_result = tool_results["compute_metric"]
            if metric_result.get("results"):
                context_parts.append("--- COMPUTED METRICS ---")
                for metric in metric_result["results"]:
                    context_parts.append(f"{metric['company']}: {metric['metric']} = {metric['value']}")
                context_parts.append("")
        
        if "list_documents" in tool_results:
            doc_result = tool_results["list_documents"]
            if doc_result.get("documents"):
                context_parts.append("--- AVAILABLE DOCUMENTS ---")
                for doc in doc_result["documents"][:5]:
                    context_parts.append(f"• {doc}")
                context_parts.append("")
        
        context = "\n".join(context_parts)
        
        # Step 4: Generate answer using tool results
        step_answer_start = time.time()
        
        system_prompt = f"""You are a financial analysis agent with access to multiple tools. You have gathered the following information:

{context}

Use this information to answer the user's question comprehensively. Reference the specific data and sources when applicable."""

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
        answer_time = time.time() - step_answer_start
        
        trace["steps"].append({
            "step": len(trace["steps"]) + 1,
            "action": "synthesize_answer",
            "status": "ok",
            "context_length": len(context),
            "elapsed_seconds": answer_time,
            "usage": result["usage"],
            "detail": {"answer_preview": result["content"][:300]},
        })
        
        trace.update({
            "tool_results": {k: {"success": "error" not in v or not v.get("error"), "count": len(v.get("results", v.get("documents", [])))} 
                           for k, v in tool_results.items()},
            "total_steps": len(trace["steps"]),
            "retrieved_chunks": retrieved,
            "prompt": system_prompt,
            "messages": [{"role": m["role"], "content": m["content"][:800]} for m in messages],
            "usage": result["usage"],
            "llm_response": True,
            "elapsed_seconds": time.time() - start_time
        })
        
        return LevelResult(
            answer=result["content"],
            citations=list(set(all_citations))[:5],
            level="agent_tools",
            trace=trace
        )
        
    except RuntimeError as e:
        if "no_key" in str(e):
            replay_result = await replay_system.get_replay_response("agent_tools", question)
            if replay_result:
                return replay_result
            
            return await replay_system.create_fallback_response(
                "agent_tools", 
                question, 
                "OpenAI API key not configured"
            )
        else:
            return await replay_system.create_fallback_response(
                "agent_tools", 
                question, 
                str(e)
            )


# Register this level
register_level(
    "agent_tools",
    10,
    "Agent Tools",
    "Advanced agent with search, metrics computation, and document listing",
    "Added compute_metric and list_documents tools for comprehensive financial analysis",
    run
)