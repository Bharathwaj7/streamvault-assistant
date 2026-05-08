from pydantic import BaseModel, Field
from typing import Optional, Any
from enum import Enum
import uuid


class MessageRole(str, Enum):
    user      = "user"
    assistant = "assistant"


class ToolCallTrace(BaseModel):
    tool_name:   str
    arguments:   dict[str, Any]
    result:      Any
    duration_ms: int


class ChatMessage(BaseModel):
    role:    MessageRole
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    history: list[ChatMessage] = Field(default_factory=list, max_length=20)


class ChatResponse(BaseModel):
    query_id:         str                 = Field(default_factory=lambda: str(uuid.uuid4()))
    answer:           str
    sources:          list[str]           = Field(default_factory=list)
    tool_traces:      list[ToolCallTrace] = Field(default_factory=list)
    model:            str
    tokens_used:      int                 = 0
    confidence:       str                 = "low"   # high | medium | low
    follow_ups:       list[str]           = Field(default_factory=list)
    escalation_level: Optional[str]       = None    # low | medium | high | None