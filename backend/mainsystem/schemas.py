from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

AgentMode = Literal["setup", "main"]


class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters_schema: Dict[str, Any] = Field(default_factory=dict)
    scopes: List[str] = Field(default_factory=list)


class PlannedAction(BaseModel):
    tool_name: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    rationale: str = ""


class AgentPlan(BaseModel):
    immediate_reply: str
    execution_goal: str
    actions: List[PlannedAction] = Field(default_factory=list)


class TaskUpdate(BaseModel):
    kind: Literal["ack", "plan", "tool", "done", "error"]
    message: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentTask(BaseModel):
    task_id: str
    session_id: str
    mode: AgentMode = "setup"
    user_input: str
    status: Literal["queued", "running", "completed", "failed"] = "queued"
    immediate_reply: str = ""
    plan: Optional[AgentPlan] = None
    updates: List[TaskUpdate] = Field(default_factory=list)
    final_message: Optional[str] = None


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    session_id: Optional[str] = None


class MemoryMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class BotProfile(BaseModel):
    bot_name: str = ""
    bot_personality: str = ""

class ChatAcceptedResponse(BaseModel):
    task_id: str
    session_id: str
    reply: str
    mode: AgentMode = "setup"
    bot_profile: BotProfile = Field(default_factory=BotProfile)
    status: Literal["accepted"] = "accepted"


class TaskStateResponse(BaseModel):
    task: AgentTask


class SessionStateResponse(BaseModel):
    session_id: str
    memory_window: List[MemoryMessage] = Field(default_factory=list)


class ToolResult(BaseModel):
    success: Optional[bool] = True
    result: Optional[str] = ""
    error_message: Optional[str] = None
