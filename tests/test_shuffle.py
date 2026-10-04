from collections import Counter

from swe_struct.graph.model import CodeGraph, Edge, EdgeKind, Node, NodeKind
from swe_struct.graph.shuffle import shuffle_edges

SIZE = 40

def synthetic_graph() -> CodeGraph:
    nodes = [Node(id="m.py", kind=NodeKind.FILE, path="m.py")]
    nodes += [Node(id=f"m.py::f{i}", kind=NodeKind.FUNCTION, path="m.py") for i in range(SIZE)]
    edges = [Edge(source="m.py", target=f"m.py::f{i}", kind=EdgeKind.CONTAINS) for i in range(SIZE)]
    edges += [
        Edge(source=f"m.py::f{i}", target=f"m.py::f{(i * i + 1) % SIZE}", kind=EdgeKind.CALLS)
        for i in range(SIZE)
    ]
    return CodeGraph(nodes, edges)

def pairs(graph: CodeGraph, kind: EdgeKind) -> list[tuple[str, str]]:
    return [(edge.source, edge.target) for edge in graph.edges if edge.kind == kind]

def test_degrees_are_preserved():
    original = synthetic_graph()
    shuffled = shuffle_edges(original, seed=1)
    before = pairs(original, EdgeKind.CALLS)
    after = pairs(shuffled, EdgeKind.CALLS)
    assert Counter(s for s, _ in before) == Counter(s for s, _ in after)
    assert Counter(t for _, t in before) == Counter(t for _, t in after)

def test_no_self_loops_or_duplicates():
    after = pairs(shuffle_edges(synthetic_graph(), seed=2), EdgeKind.CALLS)
    assert all(source != target for source, target in after)
    assert len(after) == len(set(after))

def test_containment_is_untouched():
    original = synthetic_graph()
    shuffled = shuffle_edges(original, seed=3)
    assert sorted(pairs(original, EdgeKind.CONTAINS)) == sorted(pairs(shuffled, EdgeKind.CONTAINS))

def test_shuffle_changes_the_graph_and_is_seeded():
    original = synthetic_graph()
    first = shuffle_edges(original, seed=4)
    assert pairs(first, EdgeKind.CALLS) == pairs(shuffle_edges(original, seed=4), EdgeKind.CALLS)
    assert pairs(first, EdgeKind.CALLS) != pairs(shuffle_edges(original, seed=5), EdgeKind.CALLS)
    assert set(pairs(first, EdgeKind.CALLS)) != set(pairs(original, EdgeKind.CALLS))

def test_nodes_are_unchanged():
    original = synthetic_graph()
    assert list(shuffle_edges(original, seed=6).nodes) == list(original.nodes)