import pytest

from swe_struct.core.types import RepoContext, ToolResult, ToolSpec
from swe_struct.tools.registry import ToolRegistry
from swe_struct.tools.submit import SubmitTool

class EchoTool:
    spec = ToolSpec(
        name="echo",
        description="Return the given text.",
        parameters={
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    )

    def __call__(self, ctx: RepoContext, text: str) -> ToolResult:
        return ToolResult(content=text)

@pytest.fixture
def registry() -> ToolRegistry:
    return ToolRegistry([EchoTool(), SubmitTool()])

@pytest.fixture
def ctx(tmp_path) -> RepoContext:
    return RepoContext(root=tmp_path)