from typing import Any

from pydantic import BaseModel

from swe_struct.agent.limits import Limits
from swe_struct.backends.backend import Backend
from swe_struct.core.schema import StepRecord, ToolEvent
from swe_struct.core.types import Message, RepoContext
from swe_struct.tools.registry import ToolRegistry

TRUNCATION_MARKER = "\n[output truncated]"

class AgentOutcome(BaseModel):
    steps: list[StepRecord]
    stop_reason: str
    submission: dict[str, Any] | None = None

def clip(text: str, limit: int) -> tuple[str, bool]:
    if len(text) <= limit:
        return text, False
    return text[:limit] + TRUNCATION_MARKER, True

def run_agent(
    *,
    backend: Backend,
    registry: ToolRegistry,
    ctx: RepoContext,
    messages: list[Message],
    tool_names: list[str],
    limits: Limits,
    sampling: dict[str, Any] | None = None,
) -> AgentOutcome:
    specs = registry.specs(tool_names)
    steps: list[StepRecord] = []
    submission: dict[str, Any] | None = None
    stop_reason = "max_steps"
    for index in range(limits.max_steps):
        result = backend.chat(messages, specs, **(sampling or {}))
        messages.append(
            Message(role="assistant", content=result.content, tool_calls=result.tool_calls)
        )
        events: list[ToolEvent] = []
        finished = False
        for call in result.tool_calls:
            outcome = registry.call(call.name, ctx, call.arguments)
            content, truncated = clip(outcome.content, limits.max_tool_output_chars)
            events.append(
                ToolEvent(
                    name=call.name,
                    arguments=call.arguments,
                    ok=outcome.ok,
                    result_chars=len(outcome.content),
                    truncated=truncated,
                )
            )
            messages.append(
                Message(role="tool", content=content, tool_call_id=call.id, name=call.name)
            )
            if outcome.final:
                submission = outcome.data
                finished = True
        steps.append(
            StepRecord(
                index=index,
                prompt_tokens=result.usage.prompt_tokens,
                completion_tokens=result.usage.completion_tokens,
                latency_s=result.latency_s,
                finish_reason=result.finish_reason,
                tool_events=events,
            )
        )
        if not result.tool_calls:
            stop_reason = "no_tool_call"
            break
        if finished:
            stop_reason = "submitted"
            break
    return AgentOutcome(steps=steps, stop_reason=stop_reason, submission=submission)