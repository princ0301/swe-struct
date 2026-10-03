from typing import get_args

from swe_struct.core.types import RepoContext, ToolResult, ToolSpec
from swe_struct.graph.model import CodeGraph, Direction

MAX_HOPS = 3
DEFAULT_DESCRIPTION = (
    "List symbols connected to a symbol in the repository graph: "
    "callers, callees, imports and base classes, within a number of hops."
)
RELATION_LABELS = {
    ("calls", "out"): "callee",
    ("calls", "in"): "caller",
    ("imports", "out"): "imports",
    ("imports", "in"): "imported_by",
    ("inherits", "out"): "base_class",
    ("inherits", "in"): "subclass",
}

class GraphNeighborsTool:
    def __init__(self, graph: CodeGraph, description: str = DEFAULT_DESCRIPTION) -> None:
        self._graph = graph
        self.spec = ToolSpec(
            name="graph_neighbors",
            description=description,
            parameters={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Function, class or file name."},
                    "direction": {"type": "string", "enum": list(get_args(Direction))},
                    "hops": {"type": "integer", "description": f"1 to {MAX_HOPS}."},
                },
                "required": ["symbol"],
            },
        )

    def __call__(
        self,
        ctx: RepoContext,
        symbol: str,
        direction: Direction = "both",
        hops: int = 1,
    ) -> ToolResult:
        if direction not in get_args(Direction):
            return ToolResult(content=f"invalid direction: {direction}", ok=False)
        matches = self._graph.find(symbol)
        if not matches:
            return ToolResult(content=f"symbol not found: {symbol}", ok=False)
        if len(matches) > 1:
            return ToolResult(content="ambiguous symbol, candidates:\n" + "\n".join(matches))
        reached = self._graph.neighbors(matches[0], direction, min(max(hops, 1), MAX_HOPS))
        if not reached:
            return ToolResult(content=f"{matches[0]} has no connections")
        lines = [matches[0]]
        for reach in reached:
            label = RELATION_LABELS[(reach.via.value, reach.direction)]
            lines.append(f"hop {reach.hop} {label}: {reach.node_id}")
        return ToolResult(content="\n".join(lines))