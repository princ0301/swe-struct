from pathlib import Path

import pytest

from swe_struct.graph.model import CodeGraph, Edge, EdgeKind, Node, NodeKind
from swe_struct.core.types import RepoContext, ToolResult, ToolSpec
from swe_struct.tools.registry import ToolRegistry
from swe_struct.tools.submit import SubmitTool

TINY_REPO = Path(__file__).parent / "fixtures" / "tiny_repo"

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

@pytest.fixture
def repo() -> RepoContext:
    return RepoContext(root=TINY_REPO)

@pytest.fixture
def tiny_graph() -> CodeGraph:
    nodes = [
        Node(id="app/main.py", kind=NodeKind.FILE, path="app/main.py"),
        Node(id="app/config.py", kind=NodeKind.FILE, path="app/config.py"),
        Node(id="app/base.py", kind=NodeKind.FILE, path="app/base.py"),
        Node(id="app/main.py::Runner", kind=NodeKind.CLASS, path="app/main.py"),
        Node(id="app/base.py::Base", kind=NodeKind.CLASS, path="app/base.py"),
        Node(id="app/main.py::Runner.run", kind=NodeKind.FUNCTION, path="app/main.py"),
        Node(id="app/base.py::Base.run", kind=NodeKind.FUNCTION, path="app/base.py"),
        Node(id="app/config.py::parse_config", kind=NodeKind.FUNCTION, path="app/config.py"),
        Node(id="app/config.py::load_config", kind=NodeKind.FUNCTION, path="app/config.py"),
    ]
    edges = [
        Edge(source="app/config.py::load_config", target="app/config.py::parse_config", kind=EdgeKind.CALLS),
        Edge(source="app/main.py::Runner.run", target="app/config.py::load_config", kind=EdgeKind.CALLS),
        Edge(source="app/main.py::Runner", target="app/base.py::Base", kind=EdgeKind.INHERITS),
        Edge(source="app/main.py", target="app/config.py", kind=EdgeKind.IMPORTS),
        Edge(source="app/main.py", target="app/base.py", kind=EdgeKind.IMPORTS),
    ]
    return CodeGraph(nodes, edges)