import pytest

from swe_struct.graph.model import CodeGraph, Edge, EdgeKind, Node, NodeKind

PARSE = "app/config.py::parse_config"
LOAD = "app/config.py::load_config"
RUN = "app/main.py::Runner.run"

def test_find_by_bare_name(tiny_graph):
    assert tiny_graph.find("parse_config") == [PARSE]

def test_find_by_qualified_name_and_exact_id(tiny_graph):
    assert tiny_graph.find("Runner.run") == [RUN]
    assert tiny_graph.find(RUN) == [RUN]
    assert tiny_graph.find("app/config.py") == ["app/config.py"]

def test_find_ambiguous_name_returns_all_sorted(tiny_graph):
    assert tiny_graph.find("run") == ["app/base.py::Base.run", RUN]

def test_find_unknown(tiny_graph):
    assert tiny_graph.find("nothing") == []

def test_incoming_one_hop(tiny_graph):
    reached = tiny_graph.neighbors(PARSE, "in", 1)
    assert [(r.node_id, r.hop, r.via, r.direction) for r in reached] == [
        (LOAD, 1, EdgeKind.CALLS, "in")
    ]

def test_incoming_two_hops(tiny_graph):
    reached = tiny_graph.neighbors(PARSE, "in", 2)
    assert [(r.node_id, r.hop) for r in reached] == [(LOAD, 1), (RUN, 2)]

def test_outgoing_two_hops(tiny_graph):
    reached = tiny_graph.neighbors(RUN, "out", 2)
    assert [(r.node_id, r.hop) for r in reached] == [(LOAD, 1), (PARSE, 2)]

def test_no_outgoing_from_leaf(tiny_graph):
    assert tiny_graph.neighbors(PARSE, "out", 3) == []

def test_both_directions_are_sorted_by_id(tiny_graph):
    reached = tiny_graph.neighbors(LOAD, "both", 1)
    assert [(r.node_id, r.direction) for r in reached] == [(PARSE, "out"), (RUN, "in")]

def test_inheritance_edge(tiny_graph):
    reached = tiny_graph.neighbors("app/main.py::Runner", "out", 1)
    assert [(r.node_id, r.via) for r in reached] == [("app/base.py::Base", EdgeKind.INHERITS)]

def test_each_node_is_reached_once(tiny_graph):
    ids = [r.node_id for r in tiny_graph.neighbors("app/main.py", "both", 3)]
    assert len(ids) == len(set(ids))

def test_edge_with_unknown_endpoint_raises():
    node = Node(id="a", kind=NodeKind.FILE, path="a")
    with pytest.raises(ValueError):
        CodeGraph([node], [Edge(source="a", target="b", kind=EdgeKind.CALLS)])