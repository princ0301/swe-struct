import random

from swe_struct.graph.model import CodeGraph, Edge, EdgeKind

SHUFFLED_KINDS = (EdgeKind.CALLS, EdgeKind.IMPORTS, EdgeKind.INHERITS)

def rewire(pairs: list[tuple[str, str]], rng: random.Random, attempts: int) -> list[tuple[str, str]]:
    pairs = list(pairs)
    present = set(pairs)
    for _ in range(attempts):
        if len(pairs) < 2:
            break
        first, second = rng.randrange(len(pairs)), rng.randrange(len(pairs))
        if first == second:
            continue
        (source_a, target_a), (source_b, target_b) = pairs[first], pairs[second]
        swapped_a, swapped_b = (source_a, target_b), (source_b, target_a)
        if source_a == target_b or source_b == target_a:
            continue
        if swapped_a in present or swapped_b in present:
            continue
        present -= {pairs[first], pairs[second]}
        present |= {swapped_a, swapped_b}
        pairs[first], pairs[second] = swapped_a, swapped_b
    return pairs

def shuffle_edges(graph: CodeGraph, seed: int, attempts_per_edge: int = 10) -> CodeGraph:
    rng = random.Random(seed)
    edges = [edge for edge in graph.edges if edge.kind not in SHUFFLED_KINDS]
    for kind in SHUFFLED_KINDS:
        pairs = [(edge.source, edge.target) for edge in graph.edges if edge.kind == kind]
        for source, target in rewire(pairs, rng, attempts_per_edge * len(pairs)):
            edges.append(Edge(source=source, target=target, kind=kind))
    edges.sort(key=lambda edge: (edge.source, edge.target, edge.kind.value))
    return CodeGraph(graph.nodes.values(), edges)