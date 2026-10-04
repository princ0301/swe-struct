from swe_struct.data.patch import parse_patch, patched_nodes
from swe_struct.graph.build import build_graph

PATCH = """diff --git a/app/config.py b/app/config.py
--- a/app/config.py
+++ b/app/config.py
@@ -2,3 +2,4 @@ def parse_config(text):
     result = {}
+    seen = set()
     for line in text.splitlines():
         key, _, value = line.partition("=")
@@ -8,3 +9,3 @@ def load_config(path):
 def load_config(path):
-    with open(path) as handle:
+    with open(path, encoding="utf-8") as handle:
         return parse_config(handle.read())
"""

PARSE = "app/config.py::parse_config"
LOAD = "app/config.py::load_config"

def test_parse_removed_lines_and_insertions():
    [change] = parse_patch(PATCH)
    assert change.path == "app/config.py"
    assert change.removed == [9]
    assert change.insertions == [(2, 3)]

def test_new_files_are_ignored():
    text = "diff --git a/x.py b/x.py\n--- /dev/null\n+++ b/x.py\n@@ -0,0 +1,2 @@\n+a\n+b\n"
    assert parse_patch(text) == []

def test_removed_line_that_looks_like_a_header_is_not_a_header():
    text = "--- a/f.py\n+++ b/f.py\n@@ -1,2 +1,1 @@\n--- not a header\n keep\n"
    [change] = parse_patch(text)
    assert change.removed == [1]

def test_zero_count_hunk_is_an_insertion_after_the_line():
    text = "--- a/f.py\n+++ b/f.py\n@@ -5,0 +6,2 @@\n+one\n+two\n"
    [change] = parse_patch(text)
    assert change.insertions == [(5, 6)]

def test_consecutive_added_lines_make_one_insertion():
    text = "--- a/f.py\n+++ b/f.py\n@@ -1,2 +1,4 @@\n a\n+x\n+y\n b\n"
    [change] = parse_patch(text)
    assert change.insertions == [(1, 2)]

def test_no_newline_marker_is_ignored():
    text = "--- a/f.py\n+++ b/f.py\n@@ -1,1 +1,1 @@\n-old\n\\ No newline at end of file\n+new\n\\ No newline at end of file\n"
    [change] = parse_patch(text)
    assert change.removed == [1]

def test_multiple_files():
    text = (
        "--- a/a.py\n+++ b/a.py\n@@ -1,1 +1,1 @@\n-x\n+y\n"
        "--- a/b.py\n+++ b/b.py\n@@ -3,1 +3,1 @@\n-p\n+q\n"
    )
    assert [(c.path, c.removed) for c in parse_patch(text)] == [("a.py", [1]), ("b.py", [3])]

def test_patched_nodes_map_to_functions(repo):
    graph = build_graph(repo.root).graph
    assert patched_nodes(graph, parse_patch(PATCH)) == [LOAD, PARSE]

def test_insertion_between_functions_maps_to_the_file(repo):
    graph = build_graph(repo.root).graph
    text = "--- a/app/config.py\n+++ b/app/config.py\n@@ -6,2 +6,3 @@\n     return result\n+# note\n \n"
    assert patched_nodes(graph, parse_patch(text)) == ["app/config.py"]

def test_innermost_node_wins(repo):
    graph = build_graph(repo.root).graph
    text = "--- a/app/main.py\n+++ b/app/main.py\n@@ -6,1 +6,1 @@\n-        return load_config(\"settings.cfg\")\n+        return None\n"
    assert patched_nodes(graph, parse_patch(text)) == ["app/main.py::Runner.run"]

def test_class_line_maps_to_the_class(repo):
    graph = build_graph(repo.root).graph
    text = "--- a/app/main.py\n+++ b/app/main.py\n@@ -4,1 +4,1 @@\n-class Runner(Base):\n+class Runner(Base, object):\n"
    assert patched_nodes(graph, parse_patch(text)) == ["app/main.py::Runner"]

def test_non_python_files_are_ignored(repo):
    graph = build_graph(repo.root).graph
    text = "--- a/README.md\n+++ b/README.md\n@@ -1,1 +1,1 @@\n-a\n+b\n"
    assert patched_nodes(graph, parse_patch(text)) == []