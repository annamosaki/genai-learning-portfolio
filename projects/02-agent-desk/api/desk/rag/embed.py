"""Embedding utilities for vector storage and retrieval."""

import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional
from ..llm import llm_client


class EmbeddingManager:
    """Manage embeddings for chunks."""
    
    def __init__(self):
        self.model = "text-embedding-3-small"
        
    async def create_embeddings(self, chunks: List[Dict[str, Any]]) -> np.ndarray:
        """
        Create embeddings for a list of chunks.
        
        Args:
            chunks: List of chunk dictionaries with 'text' field
            
        Returns:
            numpy array of embeddings with shape (len(chunks), embedding_dim)
        """
        if not chunks:
            return np.array([])
        
        # Extract texts
        texts = [chunk['text'] for chunk in chunks]
        
        try:
            # Use LLM client to generate embeddings
            embeddings = await llm_client.embed(texts, model=self.model)
            return embeddings
            
        except RuntimeError as e:
            if "no_key" in str(e):
                print("No OpenAI API key - generating random unit vectors for testing")
                return self._generate_random_embeddings(len(texts))
            else:
                raise
    
    def _generate_random_embeddings(self, count: int, dim: int = 1536) -> np.ndarray:
        """Generate random unit vectors for testing when no API key available."""
        # Generate random vectors
        random_vectors = np.random.randn(count, dim)
        
        # Normalize to unit vectors
        norms = np.linalg.norm(random_vectors, axis=1, keepdims=True)
        unit_vectors = random_vectors / np.maximum(norms, 1e-8)
        
        return unit_vectors
    
    def save_embeddings(self, embeddings: np.ndarray, filepath: Path):
        """Save embeddings to numpy file."""
        filepath.parent.mkdir(parents=True, exist_ok=True)
        np.save(filepath, embeddings)
        print(f"Saved embeddings to {filepath} (shape: {embeddings.shape})")
    
    def load_embeddings(self, filepath: Path) -> Optional[np.ndarray]:
        """Load embeddings from numpy file."""
        if not filepath.exists():
            return None
        
        try:
            embeddings = np.load(filepath)
            print(f"Loaded embeddings from {filepath} (shape: {embeddings.shape})")
            return embeddings
        except Exception as e:
            print(f"Error loading embeddings from {filepath}: {e}")
            return None