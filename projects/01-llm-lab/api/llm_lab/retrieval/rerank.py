"""LLM-based reranking for search results."""

import json
import time
from typing import List, Tuple, Dict, Any
from ..llm import llm_client


async def llm_listwise_rerank(
    query: str,
    chunks: List[Dict[str, Any]],
    top_k: int = 5
) -> List[Tuple[int, float, str]]:
    """
    Use LLM to rerank chunks with listwise scoring.
    
    Args:
        query: User's query
        chunks: List of chunk dictionaries with text and metadata
        top_k: Number of top results to return
    
    Returns:
        List of (original_index, relevance_score, explanation) tuples
    """
    if not chunks:
        return []
    
    # Prepare chunks for reranking prompt
    chunk_texts = []
    for i, chunk in enumerate(chunks):
        # Truncate very long chunks for the reranking prompt
        text = chunk['text'][:500] + ('...' if len(chunk['text']) > 500 else '')
        chunk_texts.append(f"[{i}] {text}")
    
    chunks_text = "\n\n".join(chunk_texts)
    
    rerank_prompt = f"""You are a search relevance expert. Given a query and a list of text chunks, rank them by relevance to the query.

Query: {query}

Text Chunks:
{chunks_text}

Please rank these chunks from most relevant to least relevant. For each chunk, provide:
1. The chunk number [0], [1], etc.
2. A relevance score from 0.0 to 1.0 (1.0 = perfectly relevant)
3. A brief explanation of relevance

Format your response as JSON:
{{
  "rankings": [
    {{"chunk_id": 0, "score": 0.9, "explanation": "Direct answer to query"}},
    {{"chunk_id": 1, "score": 0.7, "explanation": "Related but not direct"}},
    ...
  ]
}}

Only include chunks with score >= 0.3. Order by descending relevance score."""

    messages = [
        {"role": "user", "content": rerank_prompt}
    ]
    
    try:
        result = await llm_client.chat(messages, temperature=0.1, max_tokens=800)
        
        # Parse JSON response
        response_text = result["content"].strip()
        
        # Try to extract JSON from the response
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            json_text = response_text[json_start:json_end]
            ranking_data = json.loads(json_text)
            
            rankings = ranking_data.get("rankings", [])
            
            # Convert to expected format and filter by score
            results = []
            for item in rankings[:top_k]:
                chunk_id = item.get("chunk_id")
                score = item.get("score", 0.0)
                explanation = item.get("explanation", "")
                
                if chunk_id is not None and score >= 0.3:
                    results.append((chunk_id, score, explanation))
            
            return results
        
    except Exception as e:
        print(f"Error in LLM reranking: {e}")
    
    # Fallback: return original order with uniform scores
    return [(i, 0.5, "Reranking failed - original order") for i in range(min(len(chunks), top_k))]


def score_based_rerank(
    scores: List[Tuple[int, float]],
    chunks: List[Dict[str, Any]],
    top_k: int = 5
) -> List[Tuple[int, float, str]]:
    """
    Fallback reranking based on original search scores.
    
    Args:
        scores: List of (chunk_index, original_score) tuples
        chunks: List of chunk dictionaries
        top_k: Number of results to return
        
    Returns:
        List of (chunk_index, normalized_score, explanation) tuples
    """
    if not scores:
        return []
    
    # Sort by original score and normalize
    sorted_scores = sorted(scores, key=lambda x: x[1], reverse=True)
    top_scores = sorted_scores[:top_k]
    
    # Normalize scores to 0-1 range
    if len(top_scores) > 1:
        max_score = top_scores[0][1]
        min_score = top_scores[-1][1]
        score_range = max_score - min_score if max_score != min_score else 1
        
        results = []
        for chunk_idx, original_score in top_scores:
            normalized_score = (original_score - min_score) / score_range
            results.append((
                chunk_idx, 
                normalized_score, 
                f"Score-based ranking (original: {original_score:.3f})"
            ))
    else:
        results = [(top_scores[0][0], 1.0, "Single result")]
    
    return results