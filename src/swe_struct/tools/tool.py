from typing import Any, Protocol

from swe_struct.core.types import RepoContext, ToolResult, ToolSpec

class Tool(Protocol):
    spec: ToolSpec

    def __call__(self, ctx: RepoContext, *args: Any, **kwargs: Any) -> ToolResult: ...