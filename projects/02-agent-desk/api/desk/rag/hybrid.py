"""Hybrid retrieval combining BM25 and dense vector search with RRF."""

import numpy as np
from typing import List, Tuple, Dict, Any
from .bm25 import BM25


def reciprocal_rank_fusion(
    bm25_results: List[Tuple[int, float]], 
    dense_results: List[Tuple[int, float]], 
    k: int = 60
) -> List[Tuple[int, float]]:
    """
    Combine BM25 and dense search results using Reciprocal Rank Fusion.
    
    Args:
        bm25_results: List of (doc_id, score) from BM25
        dense_results: List of (doc_id, score) from dense search
        k: RRF parameter (typically 60)
    
    Returns:
        Combined results sorted by RRF score
    """
    # Create rank dictionaries
    bm25_ranks = {doc_id: rank + 1 for rank, (doc_id, _) in enumerate(bm25_results)}
    dense_ranks = {doc_id: rank + 1 for rank, (doc_id, _) in enumerate(dense_results)}
    
    # Get all unique document IDs
    all_doc_ids = set(bm25_ranks.keys()) | set(dense_ranks.keys())
    
    # Calculate RRF scores
    rrf_scores = {}
    for doc_id in all_doc_ids:
        rrf_score = 0.0
        
        if doc_id in bm25_ranks:
            rrf_score += 1.0 / (k + bm25_ranks[doc_id])
        
        if doc_id in dense_ranks:
            rrf_score += 1.0 / (k + dense_ranks[doc_id])
        
        rrf_scores[doc_id] = rrf_score
    
    # Sort by RRF score descending
    results = [(doc_id, score) for doc_id, score in rrf_scores.items()]
    results.sort(key=lambda x: x[1], reverse=True)
    
    return results


class HybridRetriever:
    """Hybrid retrieval system combining BM25 and dense vector search."""
    
    def __init__(self, bm25_index: BM25, embeddings: np.ndarray):
        self.bm25_index = bm25_index
        self.embeddings = embeddings
    
    def cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot_product / (norm_a * norm_b)
    
    async def search(
        self,
        query: str,
        query_embedding: np.ndarray,
        top_k: int = 30
    ) -> Tuple[List[Tuple[int, float]], Dict[str, Any]]:
        """
        Perform hybrid search combining BM25 and dense vector search.
        
        Returns:
            Tuple of (results, trace_info)
        """
        # BM25 search
        bm25_results = self.bm25_index.search(query, top_k)
        
        # Dense vector search
        dense_results = []
        for i, doc_embedding in enumerate(self.embeddings):
            similarity = self.cosine_similarity(query_embedding, doc_embedding)
            dense_results.append((i, similarity))
        
        dense_results.sort(key=lambda x: x[1], reverse=True)
        dense_results = dense_results[:top_k]
        
        # Combine using RRF
        combined_results = reciprocal_rank_fusion(bm25_results, dense_results)
        
        # Create trace information with ranks
        trace_info = {
            "bm25_results_count": len(bm25_results),
            "dense_results_count": len(dense_results),
            "combined_results_count": len(combined_results),
            "fusion_method": "reciprocal_rank_fusion"
        }
        
        # Add rank information for top results
        bm25_rank_map = {doc_id: rank + 1 for rank, (doc_id, _) in enumerate(bm25_results)}
        dense_rank_map = {doc_id: rank + 1 for rank, (doc_id, _) in enumerate(dense_results)}
        
        # Enhance results with rank information
        enhanced_results = []
        for doc_id, rrf_score in combined_results:
            ranks = {}
            if doc_id in bm25_rank_map:
                ranks["bm25"] = bm25_rank_map[doc_id]
            if doc_id in dense_rank_map:
                ranks["dense"] = dense_rank_map[doc_id]
            
            enhanced_results.append((doc_id, rrf_score, ranks))
        
        return enhanced_results, trace_info