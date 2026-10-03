from swe_struct.tools.graph_neighbors import GraphNeighborsTool

def test_callers_two_hops(tiny_graph, ctx):
    result = GraphNeighborsTool(tiny_graph)(ctx, symbol="parse_config", direction="in", hops=2)
    assert result.content.splitlines() == [
        "app/config.py::parse_config",
        "hop 1 caller: app/config.py::load_config",
        "hop 2 caller: app/main.py::Runner.run",
    ]

def test_callees_and_base_class_labels(tiny_graph, ctx):
    tool = GraphNeighborsTool(tiny_graph)
    assert "hop 1 callee: app/config.py::load_config" in tool(ctx, symbol="Runner.run", direction="out").content
    assert "hop 1 base_class: app/base.py::Base" in tool(ctx, symbol="Runner", direction="out").content

def test_symbol_not_found(tiny_graph, ctx):
    result = GraphNeighborsTool(tiny_graph)(ctx, symbol="nothing")
    assert not result.ok
    assert "symbol not found" in result.content

def test_ambiguous_symbol_lists_candidates(tiny_graph, ctx):
    result = GraphNeighborsTool(tiny_graph)(ctx, symbol="run")
    assert result.ok
    assert result.content.startswith("ambiguous symbol")
    assert "app/base.py::Base.run" in result.content
    assert "app/main.py::Runner.run" in result.content

def test_invalid_direction(tiny_graph, ctx):
    assert not GraphNeighborsTool(tiny_graph)(ctx, symbol="parse_config", direction="sideways").ok

def test_hops_are_clamped(tiny_graph, ctx):
    tool = GraphNeighborsTool(tiny_graph)
    assert len(tool(ctx, symbol="parse_config", direction="in", hops=99).content.splitlines()) == 3
    assert len(tool(ctx, symbol="parse_config", direction="in", hops=0).content.splitlines()) == 2

def test_node_without_connections(tiny_graph, ctx):
    result = GraphNeighborsTool(tiny_graph)(ctx, symbol="Base.run")
    assert result.content == "app/base.py::Base.run has no connections"

def test_description_is_configurable(tiny_graph):
    tool = GraphNeighborsTool(tiny_graph, description="custom")
    assert tool.spec.description == "custom"
    assert tool.spec.name == "graph_neighbors"