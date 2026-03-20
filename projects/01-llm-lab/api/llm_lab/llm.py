"""Thin OpenAI wrapper with fallback support."""

import asyncio
import time
from typing import Dict, List, Any, Optional
import numpy as np
import openai
from openai import OpenAI
from .config import settings


class LLMClient:
    """Thin wrapper around OpenAI API with usage tracking."""
    
    def __init__(self):
        self.client: Optional[OpenAI] = None
        self._setup_client()
        
    def _setup_client(self):
        """Initialize OpenAI client if API key is available."""
        if settings.openai_api_key:
            self.client = OpenAI(api_key=settings.openai_api_key)
        else:
            self.client = None
    
    def has_api_key(self) -> bool:
        """Check if OpenAI API key is configured."""
        return self.client is not None
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 600,
        model: str = "gpt-4o-mini"
    ) -> Dict[str, Any]:
        """
        Send chat completion request to OpenAI.
        
        Returns:
            Dict with 'content' and 'usage' keys
            
        Raises:
            RuntimeError: If no API key is configured
        """
        if not self.client:
            raise RuntimeError("no_key")
        
        try:
            start_time = time.time()
            
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            elapsed_time = time.time() - start_time
            
            return {
                "content": response.choices[0].message.content or "",
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0,
                    "elapsed_seconds": elapsed_time,
                    "model": model
                }
            }
            
        except Exception as e:
            # Re-raise as RuntimeError for consistent error handling
            raise RuntimeError(f"openai_error: {str(e)}")
    
    async def embed(
        self,
        texts: List[str],
        model: str = "text-embedding-3-small"
    ) -> np.ndarray:
        """
        Generate embeddings for texts.
        
        Returns:
            numpy array of shape (len(texts), embedding_dim)
            
        Raises:
            RuntimeError: If no API key is configured
        """
        if not self.client:
            raise RuntimeError("no_key")
        
        if not texts:
            return np.array([])
        
        try:
            response = self.client.embeddings.create(
                model=model,
                input=texts
            )
            
            embeddings = [item.embedding for item in response.data]
            return np.array(embeddings)
            
        except Exception as e:
            raise RuntimeError(f"openai_error: {str(e)}")
    
    async def embed_single(self, text: str, model: str = "text-embedding-3-small") -> np.ndarray:
        """Generate embedding for a single text."""
        embeddings = await self.embed([text], model)
        return embeddings[0] if len(embeddings) > 0 else np.array([])


# Global LLM client instance
llm_client = LLMClient()