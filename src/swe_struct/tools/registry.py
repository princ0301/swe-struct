from collections.abc import Iterable
from typing import Any

from swe_struct.core.types import RepoContext, ToolResult, ToolSpec
from swe_struct.tools.tool import Tool

class ToolRegistry:
    def __init__(self, tools: Iterable[Tool] = ()) -> None:
        self._tools: dict[str, Tool] = {}
        for tool in tools:
            self.register(tool)

    def register(self, tool: Tool) -> None:
        if tool.spec.name in self._tools:
            raise ValueError(f"duplicate tool: {tool.spec.name}")
        self._tools[tool.spec.name] = tool

    def specs(self, names: Iterable[str]) -> list[ToolSpec]:
        return [self._tools[name].spec for name in names]

    def call(self, name: str, ctx: RepoContext, arguments: dict[str, Any]) -> ToolResult:
        tool = self._tools.get(name)
        if tool is None:
            return ToolResult(content=f"unknown tool: {name}", ok=False)
        try:
            return tool(ctx, **arguments)
        except TypeError as error:
            return ToolResult(content=f"invalid arguments: {error}", ok=False)