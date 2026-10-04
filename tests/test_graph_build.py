import warnings
from pathlib import Path

from swe_struct.graph.build import build_graph

BASE_RUN = "app/base.py::Base.run"
RUNNER = "app/main.py::Runner"
RUNNER_RUN = "app/main.py::Runner.run"
PARSE = "app/config.py::parse_config"
LOAD = "app/config.py::load_config"

def write(root: Path, files: dict[str, str]) -> Path:
    for relative, text in files.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
    return root

def edge_set(graph) -> set[tuple[str, str, str]]:
    return {(edge.source, edge.target, edge.kind.value) for edge in graph.edges}

def test_tiny_repo_nodes(repo):
    graph = build_graph(repo.root).graph
    assert set(graph.nodes) == {
        "app/__init__.py",
        "app/base.py",
        "app/config.py",
        "app/main.py",
        "app/base.py::Base",
        BASE_RUN,
        RUNNER,
        RUNNER_RUN,
        PARSE,
        LOAD,
    }

def test_tiny_repo_edges(repo):
    graph = build_graph(repo.root).graph
    assert edge_set(graph) == {
        ("app/base.py", "app/base.py::Base", "contains"),
        ("app/base.py::Base", BASE_RUN, "contains"),
        ("app/config.py", PARSE, "contains"),
        ("app/config.py", LOAD, "contains"),
        ("app/main.py", RUNNER, "contains"),
        (RUNNER, RUNNER_RUN, "contains"),
        ("app/main.py", "app/base.py", "imports"),
        ("app/main.py", "app/config.py", "imports"),
        (RUNNER, "app/base.py::Base", "inherits"),
        (LOAD, PARSE, "calls"),
        (RUNNER_RUN, LOAD, "calls"),
    }

def test_tiny_repo_stats(repo):
    stats = build_graph(repo.root).stats
    assert stats.files == 4
    assert stats.parse_failures == 0
    assert stats.imports_internal == 2
    assert stats.imports_external == 0
    assert (stats.calls_resolved, stats.calls_dynamic, stats.calls_external) == (2, 5, 1)
    assert round(stats.call_resolution_rate(), 3) == round(2 / 7, 3)

def test_node_spans_are_recorded(repo):
    graph = build_graph(repo.root).graph
    assert (graph.nodes[PARSE].start_line, graph.nodes[PARSE].end_line) == (1, 6)
    assert (graph.nodes[LOAD].start_line, graph.nodes[LOAD].end_line) == (8, 10)

def test_build_is_deterministic(repo):
    first = build_graph(repo.root).graph
    second = build_graph(repo.root).graph
    assert [edge.model_dump() for edge in first.edges] == [edge.model_dump() for edge in second.edges]
    assert list(first.nodes) == list(second.nodes)

def test_relative_import_and_call(tmp_path):
    write(
        tmp_path,
        {
            "pkg/__init__.py": "",
            "pkg/a.py": "from .b import helper\n\ndef f():\n    return helper()\n",
            "pkg/b.py": "def helper():\n    pass\n",
        },
    )
    edges = edge_set(build_graph(tmp_path).graph)
    assert ("pkg/a.py", "pkg/b.py", "imports") in edges
    assert ("pkg/a.py::f", "pkg/b.py::helper", "calls") in edges

def test_module_alias_calls(tmp_path):
    write(
        tmp_path,
        {
            "pkg/__init__.py": "",
            "pkg/b.py": "def helper():\n    pass\n",
            "pkg/a.py": "import pkg.b as pb\nfrom pkg import b\n\ndef f():\n    pb.helper()\n\ndef g():\n    b.helper()\n",
        },
    )
    edges = edge_set(build_graph(tmp_path).graph)
    assert ("pkg/a.py::f", "pkg/b.py::helper", "calls") in edges
    assert ("pkg/a.py::g", "pkg/b.py::helper", "calls") in edges

def test_self_call_resolves_through_base_class(tmp_path):
    write(
        tmp_path,
        {
            "base.py": "class A:\n    def m(self):\n        pass\n",
            "sub.py": "from base import A\n\nclass B(A):\n    def n(self):\n        self.m()\n",
        },
    )
    edges = edge_set(build_graph(tmp_path).graph)
    assert ("sub.py::B", "base.py::A", "inherits") in edges
    assert ("sub.py::B.n", "base.py::A.m", "calls") in edges

def test_class_instantiation_links_to_class(tmp_path):
    write(tmp_path, {"m.py": "class K:\n    pass\n\ndef make():\n    return K()\n"})
    assert ("m.py::make", "m.py::K", "calls") in edge_set(build_graph(tmp_path).graph)

def test_syntax_error_file_keeps_its_node(tmp_path):
    write(tmp_path, {"good.py": "def f():\n    pass\n", "bad.py": "def (:\n"})
    result = build_graph(tmp_path)
    assert result.stats.parse_failures == 1
    assert "bad.py" in result.graph.nodes
    assert "good.py::f" in result.graph.nodes

def test_ambiguous_module_suffix_is_not_resolved(tmp_path):
    write(
        tmp_path,
        {
            "a/utils.py": "def x():\n    pass\n",
            "b/utils.py": "def x():\n    pass\n",
            "c.py": "from utils import x\n",
        },
    )
    result = build_graph(tmp_path)
    assert result.stats.imports_external == 1
    assert not any(edge.source == "c.py" for edge in result.graph.edges)

def test_nested_function_owns_its_calls(tmp_path):
    write(
        tmp_path,
        {"m.py": "def helper():\n    pass\n\ndef outer():\n    def inner():\n        helper()\n    return inner\n"},
    )
    edges = edge_set(build_graph(tmp_path).graph)
    assert ("m.py::outer", "m.py::outer.inner", "contains") in edges
    assert ("m.py::outer.inner", "m.py::helper", "calls") in edges
    assert ("m.py::outer", "m.py::helper", "calls") not in edges

def test_definitions_inside_try_are_found(tmp_path):
    write(tmp_path, {"m.py": "try:\n    def f():\n        pass\nexcept Exception:\n    pass\n"})
    assert "m.py::f" in build_graph(tmp_path).graph.nodes

def test_invalid_escape_warnings_are_silenced(tmp_path):
    source = r'PATTERN = "\d+ \w"' + "\n\ndef f():\n    pass\n"
    write(tmp_path, {"m.py": source})
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        result = build_graph(tmp_path)
    assert "m.py::f" in result.graph.nodes