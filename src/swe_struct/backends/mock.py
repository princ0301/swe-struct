from typing import Any

from swe_struct.core.types import ChatResult, Message, ToolCall, ToolSpec

def text_reply(text: str) -> ChatResult:
    return ChatResult(content=text)

def tool_reply(name: str, arguments: dict[str, Any], call_id: str = "call_0") -> ChatResult:
    return ChatResult(
        tool_calls=[ToolCall(id=call_id, name=name, arguments=arguments)],
        finish_reason="tool_calls",
    )

class MockBackend:
    def __init__(self, script: list[ChatResult]) -> None:
        self._script = list(script)
        self.calls: list[list[Message]] = []

    def chat(self, messages: list[Message], tools: list[ToolSpec], **sampling: Any) -> ChatResult:
        self.calls.append(list(messages))
        if not self._script:
            raise RuntimeError("mock script exhausted")
        return self._script.pop(0)