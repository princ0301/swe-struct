from typing import Any, Protocol

from swe_struct.core.types import ChatResult, Message, ToolSpec

class Backend(Protocol):
    def chat(
        self, messages: list[Message], tools: list[ToolSpec], **sampling: Any
    ) -> ChatResult: ...