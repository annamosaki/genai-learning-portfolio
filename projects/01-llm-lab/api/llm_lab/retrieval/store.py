"""Data store for loading chunks, embeddings, and other indexed data."""

import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional
from ..config import settings
from ..models import ChunkHit


class DataStore:
    """Centralized store for indexed data."""
    
    def __init__(self):
        self.index_dir = Path(settings.index_dir)
        self._chunks_cache: Optional[List[Dict[str, Any]]] = None
        self._embeddings_cache: Optional[np.ndarray] = None
        self._figures_cache: Optional[Dict[str, Any]] = None
        self._bm25_cache: Optional[Dict[str, Any]] = None
        self._graph_cache: Optional[Dict[str, Any]] = None
        self._communities_cache: Optional[List[Dict[str, Any]]] = None
    
    def load_chunks(self) -> List[Dict[str, Any]]:
        """Load chunk data from chunks.json."""
        if self._chunks_cache is not None:
            return self._chunks_cache
        
        chunks_file = self.index_dir / "chunks.json"
        if not chunks_file.exists():
            return []
        
        try:
            with open(chunks_file, 'r') as f:
                self._chunks_cache = json.load(f)
                return self._chunks_cache
        except Exception as e:
            print(f"Error loading chunks: {e}")
            return []
    
    def load_embeddings(self) -> Optional[np.ndarray]:
        """Load embeddings from embeddings.npy."""
        if self._embeddings_cache is not None:
            return self._embeddings_cache
        
        embeddings_file = self.index_dir / "embeddings.npy"
        if not embeddings_file.exists():
            return None
        
        try:
            self._embeddings_cache = np.load(embeddings_file)
            return self._embeddings_cache
        except Exception as e:
            print(f"Error loading embeddings: {e}")
            return None
    
    def load_figures(self) -> Dict[str, Any]:
        """Load financial figures from figures.json."""
        if self._figures_cache is not None:
            return self._figures_cache
        
        figures_file = self.index_dir / "figures.json"
        if not figures_file.exists():
            return {}
        
        try:
            with open(figures_file, 'r') as f:
                self._figures_cache = json.load(f)
                return self._figures_cache
        except Exception as e:
            print(f"Error loading figures: {e}")
            return {}
    
    def load_bm25_index(self) -> Optional[Dict[str, Any]]:
        """Load BM25 index from bm25.json."""
        if self._bm25_cache is not None:
            return self._bm25_cache
        
        bm25_file = self.index_dir / "bm25.json"
        if not bm25_file.exists():
            return None
        
        try:
            with open(bm25_file, 'r') as f:
                self._bm25_cache = json.load(f)
                return self._bm25_cache
        except Exception as e:
            print(f"Error loading BM25 index: {e}")
            return None
    
    def load_graph(self) -> Optional[Dict[str, Any]]:
        """Load graph data from graph.json."""
        if self._graph_cache is not None:
            return self._graph_cache
        
        graph_file = self.index_dir / "graph.json"
        if not graph_file.exists():
            return None
        
        try:
            with open(graph_file, 'r') as f:
                self._graph_cache = json.load(f)
                return self._graph_cache
        except Exception as e:
            print(f"Error loading graph: {e}")
            return None
    
    def load_communities(self) -> List[Dict[str, Any]]:
        """Load community data from communities.json."""
        if self._communities_cache is not None:
            return self._communities_cache
        
        communities_file = self.index_dir / "communities.json"
        if not communities_file.exists():
            return []
        
        try:
            with open(communities_file, 'r') as f:
                self._communities_cache = json.load(f)
                return self._communities_cache
        except Exception as e:
            print(f"Error loading communities: {e}")
            return []
    
    def clear_cache(self):
        """Clear all cached data."""
        self._chunks_cache = None
        self._embeddings_cache = None
        self._figures_cache = None
        self._bm25_cache = None
        self._graph_cache = None
        self._communities_cache = None


# Global data store instance
data_store = DataStore()