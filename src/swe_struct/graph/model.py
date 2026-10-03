from collections import defaultdict
from collections.abc import Iterable
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel

Direction = Literal["out", "in", "both"]

class NodeKind(StrEnum):
    FILE = "file"
    CLASS = "class"
    FUNCTION = "function"

class EdgeKind(StrEnum):
    CALLS = "calls"
    IMPORTS = "imports"
    INHERITS = "inherits"

class Node(BaseModel):
    id: str
    kind: NodeKind
    path: str

class Edge(BaseModel):
    source: str
    target: str
    kind: EdgeKind

class Reach(BaseModel):
    node_id: str
    hop: int
    via: EdgeKind
    direction: Literal["out", "in"]

class CodeGraph:
    def __init__(self, nodes: Iterable[Node], edges: Iterable[Edge]) -> None:
        self.nodes = {node.id: node for node in nodes}
        self.edges = list(edges)
        self._out: dict[str, list[tuple[str, EdgeKind]]] = defaultdict(list)
        self._in: dict[str, list[tuple[str, EdgeKind]]] = defaultdict(list)
        for edge in self.edges:
            if edge.source not in self.nodes or edge.target not in self.nodes:
                raise ValueError(f"edge endpoint missing: {edge.source} -> {edge.target}")
            self._out[edge.source].append((edge.target, edge.kind))
            self._in[edge.target].append((edge.source, edge.kind))

    def find(self, query: str) -> list[str]:
        if query in self.nodes:
            return [query]
        matches = []
        for node_id in self.nodes:
            qualified = node_id.split("::", 1)[-1]
            if qualified == query or qualified.endswith("." + query):
                matches.append(node_id)
        return sorted(matches)

    def neighbors(self, node_id: str, direction: Direction = "both", max_hops: int = 1) -> list[Reach]:
        sides: list[tuple[Literal["out", "in"], dict[str, list[tuple[str, EdgeKind]]]]] = []
        if direction in ("out", "both"):
            sides.append(("out", self._out))
        if direction in ("in", "both"):
            sides.append(("in", self._in))
        visited = {node_id}
        frontier = [node_id]
        reached: list[Reach] = []
        for hop in range(1, max_hops + 1):
            found: list[Reach] = []
            for current in sorted(frontier):
                for side, adjacency in sides:
                    for other, kind in sorted(adjacency.get(current, [])):
                        if other in visited:
                            continue
                        visited.add(other)
                        found.append(Reach(node_id=other, hop=hop, via=kind, direction=side))
            found.sort(key=lambda reach: reach.node_id)
            reached.extend(found)
            frontier = [reach.node_id for reach in found]
            if not frontier:
                break
        return reached