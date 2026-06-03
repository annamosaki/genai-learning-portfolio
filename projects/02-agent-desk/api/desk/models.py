"""Data models for Agent Desk."""

from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel
from datetime import datetime
from enum import Enum


class AgentType(str, Enum):
    """Types of agents in the desk."""
    RESEARCH = "research"
    MACRO = "macro"
    QUANT = "quant"
    RISK = "risk"
    SCRIBE = "scribe"


class EventType(str, Enum):
    """Types of events in the orchestration."""
    AGENT_DISCOVERED = "agent.discovered"
    TASK_CREATED = "task.created"
    MESSAGE_SENT = "message.sent"
    MESSAGE_RECEIVED = "message.received"
    TOOL_CALLED = "tool.called"
    TOOL_RETURNED = "tool.returned"
    APPROVAL_REQUIRED = "approval.required"
    APPROVAL_RESOLVED = "approval.resolved"
    AGENT_FINISHED = "agent.finished"
    RUN_FINISHED = "run.finished"
    TOKEN_USAGE = "token.usage"


class ApprovalDecision(str, Enum):
    """Approval decisions."""
    APPROVE = "approve"
    EDIT = "edit"
    DENY = "deny"


class RunRequest(BaseModel):
    """Request to start a new analysis run."""
    ticker: str
    question: Optional[str] = "Provide a comprehensive investment analysis"
    mode: Literal["live", "replay"] = "live"


class ApprovalRequest(BaseModel):
    """Request to approve/deny a gate."""
    tool_call_id: str
    decision: ApprovalDecision
    override_args: Optional[Dict[str, Any]] = None
    message: Optional[str] = None


class Event(BaseModel):
    """Base event structure."""
    type: EventType
    timestamp: datetime
    run_id: str
    agent: Optional[str] = None
    data: Dict[str, Any] = {}


class AgentMessage(BaseModel):
    """Message between agents."""
    from_agent: str
    to_agent: str
    content: str
    timestamp: datetime
    tool_calls: Optional[List[Dict[str, Any]]] = None


class ToolCall(BaseModel):
    """Tool call information."""
    id: str
    name: str
    args: Dict[str, Any]
    result: Optional[Any] = None
    error: Optional[str] = None


class ApprovalGate(BaseModel):
    """Approval gate information."""
    id: str
    type: Literal["plan", "memo"]
    description: str
    content: str
    required_approvals: int = 1
    approvals: List[ApprovalRequest] = []
    status: Literal["pending", "approved", "denied"] = "pending"


class RunState(BaseModel):
    """State of an analysis run."""
    id: str
    ticker: str
    question: str
    status: Literal["running", "waiting_approval", "completed", "failed"] = "running"
    created_at: datetime
    updated_at: datetime
    events: List[Event] = []
    agents: Dict[str, Dict[str, Any]] = {}
    approvals: Dict[str, ApprovalGate] = {}
    final_memo: Optional[str] = None
    started: bool = False


class ChunkHit(BaseModel):
    """Search result chunk."""
    chunk_id: str
    content: str
    score: float
    source_file: str
    metadata: Dict[str, Any] = {}


class AgentCard(BaseModel):
    """A2A agent card."""
    name: str
    description: str
    version: str = "1.0.0"
    capabilities: List[str]
    tools: List[Dict[str, Any]] = []
    endpoints: Dict[str, str] = {}