from collections.abc import Iterable
from enum import StrEnum

from swe_struct.graph.model import CodeGraph, EdgeKind

class HopBucket(StrEnum):
    ZERO_OR_ONE = "0-1"
    TWO = "2"
    THREE_PLUS = "3+"
    DISCONNECTED = "disconnected"
    NO_ANCHOR = "no_anchor"

def hop_distance(
    graph: CodeGraph,
    sources: Iterable[str],
    targets: Iterable[str],
    max_hops: int = 6,
    kinds: frozenset[EdgeKind] | None = None,
) -> int | None:
    target_set = set(targets) & graph.nodes.keys()
    frontier = set(sources) & graph.nodes.keys()
    if not frontier or not target_set:
        return None
    visited = set(frontier)
    for distance in range(max_hops + 1):
        if frontier & target_set:
            return distance
        following: set[str] = set()
        for node_id in frontier:
            for other in graph.adjacent(node_id, kinds):
                if other not in visited:
                    visited.add(other)
                    following.add(other)
        frontier = following
        if not frontier:
            break
    return None

def bucket_for(has_anchor: bool, distance: int | None) -> HopBucket:
    if not has_anchor:
        return HopBucket.NO_ANCHOR
    if distance is None:
        return HopBucket.DISCONNECTED
    if distance <= 1:
        return HopBucket.ZERO_OR_ONE
    if distance == 2:
        return HopBucket.TWO
    return HopBucket.THREE_PLUS