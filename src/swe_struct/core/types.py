from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

class ToolCall(BaseModel):
    id: str
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)

class Message(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str | None = None
    tool_calls: list[ToolCall] = Field(default_factory=list)
    tool_call_id: str | None = None
    name: str | None = None

class ToolSpec(BaseModel):
    name: str
    description: str
    parameters: dict[str, Any]

    def to_wire(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

class ToolResult(BaseModel):
    content: str
    ok: bool = True
    final: bool = False
    data: dict[str, Any] | None = None

class Usage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0

class ChatResult(BaseModel):
    content: str | None = None
    tool_calls: list[ToolCall] = Field(default_factory=list)
    usage: Usage = Field(default_factory=Usage)
    latency_s: float = 0.0
    finish_reason: str = "stop"

class RepoContext(BaseModel):
    root: Path