from swe_struct.graph.build import build_graph
from swe_struct.graph.hops import HopBucket, bucket_for, hop_distance
from swe_struct.graph.model import EdgeKind

PARSE = "app/config.py::parse_config"
LOAD = "app/config.py::load_config"
RUN = "app/main.py::Runner.run"

def test_same_node_is_distance_zero(tiny_graph):
    assert hop_distance(tiny_graph, [PARSE], [PARSE]) == 0

def test_two_hops_across_calls(tiny_graph):
    assert hop_distance(tiny_graph, [PARSE], [RUN]) == 2

def test_multiple_sources_use_the_closest(tiny_graph):
    assert hop_distance(tiny_graph, [PARSE, LOAD], [RUN]) == 1

def test_max_hops_cuts_the_search(tiny_graph):
    assert hop_distance(tiny_graph, [PARSE], [RUN], max_hops=1) is None

def test_disconnected_and_empty_inputs(tiny_graph):
    assert hop_distance(tiny_graph, ["app/base.py::Base.run"], [PARSE]) is None
    assert hop_distance(tiny_graph, [], [PARSE]) is None
    assert hop_distance(tiny_graph, ["unknown"], [PARSE]) is None

def test_edge_kind_filter(tiny_graph):
    assert hop_distance(tiny_graph, [PARSE], [RUN], kinds=frozenset({EdgeKind.CALLS})) == 2
    assert hop_distance(tiny_graph, [PARSE], [RUN], kinds=frozenset({EdgeKind.IMPORTS})) is None

def test_distance_on_built_graph_uses_contains_edges(repo):
    graph = build_graph(repo.root).graph
    assert hop_distance(graph, [PARSE], [LOAD]) == 1
    assert hop_distance(graph, [PARSE], [RUN]) == 2
    assert hop_distance(graph, ["app/base.py::Base.run"], [PARSE]) == 5

def test_buckets():
    assert bucket_for(False, None) == HopBucket.NO_ANCHOR
    assert bucket_for(True, None) == HopBucket.DISCONNECTED
    assert bucket_for(True, 0) == HopBucket.ZERO_OR_ONE
    assert bucket_for(True, 1) == HopBucket.ZERO_OR_ONE
    assert bucket_for(True, 2) == HopBucket.TWO
    assert bucket_for(True, 5) == HopBucket.THREE_PLUS