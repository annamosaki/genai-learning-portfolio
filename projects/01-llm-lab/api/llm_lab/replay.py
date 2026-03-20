"""Replay system for fallback when OpenAI API is unavailable."""

import json
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional
from .config import settings
from .models import LevelResult


class ReplaySystem:
    """Load and serve pre-recorded responses when API is unavailable."""
    
    def __init__(self):
        self.replay_dir = Path(settings.replay_dir)
        self._cache: Dict[str, Dict[str, Any]] = {}
        
    def _load_replay_file(self, level: str) -> Optional[Dict[str, Any]]:
        """Load replay data for a specific level."""
        if level in self._cache:
            return self._cache[level]
        
        replay_file = self.replay_dir / f"{level}.json"
        if not replay_file.exists():
            return None
        
        try:
            with open(replay_file, 'r') as f:
                data = json.load(f)
                self._cache[level] = data
                return data
        except Exception as e:
            print(f"Error loading replay file for {level}: {e}")
            return None
    
    async def get_replay_response(
        self,
        level: str,
        question: str,
        history_length: int = 0
    ) -> Optional[LevelResult]:
        """
        Get a replay response for the given level and question.
        
        Args:
            level: The level identifier (e.g., "stateless", "naive-rag")
            question: The user's question
            history_length: Length of conversation history
            
        Returns:
            LevelResult if replay data exists, None otherwise
        """
        replay_data = self._load_replay_file(level)
        if not replay_data:
            return None
        
        # Try to find a matching response
        responses = replay_data.get("responses", [])
        if not responses:
            return None
        
        # For now, return the first response
        # In a more sophisticated system, we might match by question similarity
        first_response = responses[0]
        
        # Add replay indicator to trace
        trace = first_response.get("trace", {})
        trace.update({
            "replay": True,
            "replay_reason": "OpenAI API unavailable",
            "original_question": question
        })
        
        return LevelResult(
            answer=first_response.get("answer", "I apologize, but I'm currently running in demo mode without API access. This is a pre-recorded response."),
            citations=first_response.get("citations", []),
            level=level,
            trace=trace
        )
    
    async def create_fallback_response(
        self,
        level: str,
        question: str,
        error_message: str = ""
    ) -> LevelResult:
        """
        Create a fallback response when no replay data is available.
        """
        fallback_answer = (
            f"I'm currently running in demo mode. "
            f"This {level} level would normally process your question about: \"{question[:100]}...\""
            f"{' Error: ' + error_message if error_message else ''}"
        )
        
        return LevelResult(
            answer=fallback_answer,
            citations=[],
            level=level,
            trace={
                "fallback": True,
                "reason": error_message or "OpenAI API unavailable",
                "level_attempted": level
            }
        )


# Global replay system instance
replay_system = ReplaySystem()