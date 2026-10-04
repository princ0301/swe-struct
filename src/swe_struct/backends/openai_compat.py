import json
import time
from typing import Any

import httpx

from swe_struct.core.types import ChatResult, Message, ToolCall, ToolSpec, Usage

def message_to_wire(message: Message) -> dict[str, Any]:
    wire: dict[str, Any] = {"role": message.role, "content": message.content or ""}
    if message.tool_calls:
        wire["tool_calls"] = [
            {
                "id": call.id,
                "type": "function",
                "function": {"name": call.name, "arguments": json.dumps(call.arguments)},
            }
            for call in message.tool_calls
        ]
    if message.tool_call_id is not None:
        wire["tool_call_id"] = message.tool_call_id
    if message.name is not None:
        wire["name"] = message.name
    return wire

def parse_arguments(raw: Any) -> dict[str, Any]:
    if not raw:
        return {}
    if isinstance(raw, dict):
        return raw
    try:
        parsed = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return {"_raw": raw}
    return parsed if isinstance(parsed, dict) else {"_raw": raw}

def parse_response(payload: dict[str, Any], latency_s: float) -> ChatResult:
    choice = payload["choices"][0]
    message = choice["message"]
    calls = [
        ToolCall(
            id=raw.get("id") or f"call_{index}",
            name=raw["function"]["name"],
            arguments=parse_arguments(raw["function"].get("arguments")),
        )
        for index, raw in enumerate(message.get("tool_calls") or [])
    ]
    usage = payload.get("usage") or {}
    return ChatResult(
        content=message.get("content"),
        tool_calls=calls,
        usage=Usage(
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
        ),
        latency_s=latency_s,
        finish_reason=choice.get("finish_reason") or "stop",
    )

class OpenAICompatBackend:
    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str | None = None,
        timeout_s: float = 600.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.model = model
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self._client = client or httpx.Client(
            base_url=base_url.rstrip("/") + "/", headers=headers, timeout=timeout_s
        )

    def chat(self, messages: list[Message], tools: list[ToolSpec], **sampling: Any) -> ChatResult:
        body: dict[str, Any] = {
            "model": self.model,
            "messages": [message_to_wire(message) for message in messages],
            **sampling,
        }
        if tools:
            body["tools"] = [tool.to_wire() for tool in tools]
            body.setdefault("tool_choice", "auto")
        start = time.perf_counter()
        response = self._client.post("chat/completions", json=body)
        response.raise_for_status()
        return parse_response(response.json(), time.perf_counter() - start)