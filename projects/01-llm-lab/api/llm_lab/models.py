"""Pydantic models for LLM Lab API."""

from pydantic import BaseModel, Field
from typing import Literal, Any
from enum import Enum


class Turn(BaseModel):
    """A single conversation turn."""
    role: Literal["user", "assistant"]
    content: str


class LevelOpts(BaseModel):
    """Options for level execution."""
    security_tier: Literal["none", "hardened", "guarded"] = "none"
    search_mode: Literal["local", "global", "both"] = "both"


class ChunkHit(BaseModel):
    """A search result chunk."""
    id: str
    text: str
    score: float
    source: str | None = None
    ranks: dict[str, int] | None = None


class LevelResult(BaseModel):
    """Result from a level execution."""
    answer: str
    citations: list[str] = []
    level: str
    trace: dict[str, Any] = {}  # flexible: prompt, chunks, timings, tokens, cost, graph, steps, security, etc.


class ChatRequest(BaseModel):
    """Chat API request."""
    level: str
    question: str
    history: list[Turn] = []
    opts: LevelOpts = LevelOpts()


class ChatResponse(BaseModel):
    """Chat API response."""
    result: LevelResult
    status: str = "success"
    error: str | None = None


class CompareRequest(BaseModel):
    """Compare multiple levels request."""
    levels: list[str]
    question: str
    history: list[Turn] = []
    opts: LevelOpts = LevelOpts()


class CompareResponse(BaseModel):
    """Compare multiple levels response."""
    results: dict[str, LevelResult]
    status: str = "success"
    errors: dict[str, str] = {}


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    has_openai_key: bool
    uptime_seconds: float


class LevelInfo(BaseModel):
    """Information about a level."""
    id: str
    number: int
    title: str
    blurb: str
    what_changed: str


class LevelsResponse(BaseModel):
    """List of available levels."""
    levels: list[LevelInfo]