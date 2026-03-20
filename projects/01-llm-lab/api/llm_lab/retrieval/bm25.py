"""Pure Python BM25 implementation for text retrieval."""

import math
import json
from collections import defaultdict, Counter
from typing import List, Dict, Tuple, Any
import re


class BM25:
    """BM25 ranking function implementation."""
    
    def __init__(self, k1: float = 1.2, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.documents: List[List[str]] = []
        self.doc_lengths: List[int] = []
        self.avg_doc_length: float = 0
        self.document_frequencies: Dict[str, int] = {}
        self.num_docs: int = 0
        
    def tokenize(self, text: str) -> List[str]:
        """Simple tokenization - split on whitespace and punctuation."""
        # Convert to lowercase and split on non-alphanumeric characters
        tokens = re.findall(r'\b\w+\b', text.lower())
        return tokens
    
    def fit(self, documents: List[str]):
        """Fit BM25 on a corpus of documents."""
        self.documents = [self.tokenize(doc) for doc in documents]
        self.doc_lengths = [len(doc) for doc in self.documents]
        self.avg_doc_length = sum(self.doc_lengths) / len(self.doc_lengths) if self.doc_lengths else 0
        self.num_docs = len(documents)
        
        # Calculate document frequencies
        self.document_frequencies = defaultdict(int)
        for doc in self.documents:
            unique_tokens = set(doc)
            for token in unique_tokens:
                self.document_frequencies[token] += 1
    
    def score_document(self, query_tokens: List[str], doc_idx: int) -> float:
        """Calculate BM25 score for a document given query tokens."""
        if doc_idx >= len(self.documents):
            return 0.0
        
        document = self.documents[doc_idx]
        doc_length = self.doc_lengths[doc_idx]
        
        score = 0.0
        term_counts = Counter(document)
        
        for token in query_tokens:
            if token not in term_counts:
                continue
            
            # Term frequency in document
            tf = term_counts[token]
            
            # Document frequency (number of documents containing the term)
            df = self.document_frequencies.get(token, 0)
            if df == 0:
                continue
            
            # Inverse document frequency
            idf = math.log((self.num_docs - df + 0.5) / (df + 0.5))
            
            # BM25 score component
            score += idf * (tf * (self.k1 + 1)) / (tf + self.k1 * (1 - self.b + self.b * doc_length / self.avg_doc_length))
        
        return score
    
    def search(self, query: str, top_k: int = 10) -> List[Tuple[int, float]]:
        """Search for documents matching the query."""
        query_tokens = self.tokenize(query)
        if not query_tokens:
            return []
        
        scores = []
        for doc_idx in range(self.num_docs):
            score = self.score_document(query_tokens, doc_idx)
            scores.append((doc_idx, score))
        
        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize BM25 index to dictionary."""
        return {
            "k1": self.k1,
            "b": self.b,
            "documents": self.documents,
            "doc_lengths": self.doc_lengths,
            "avg_doc_length": self.avg_doc_length,
            "document_frequencies": dict(self.document_frequencies),
            "num_docs": self.num_docs
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BM25':
        """Load BM25 index from dictionary."""
        bm25 = cls(k1=data["k1"], b=data["b"])
        bm25.documents = data["documents"]
        bm25.doc_lengths = data["doc_lengths"]
        bm25.avg_doc_length = data["avg_doc_length"]
        bm25.document_frequencies = defaultdict(int, data["document_frequencies"])
        bm25.num_docs = data["num_docs"]
        return bm25