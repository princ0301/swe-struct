from swe_struct.data.anchors import extract_tokens, find_anchors, is_code_like
from swe_struct.graph.build import build_graph

PARSE = "app/config.py::parse_config"
LOAD = "app/config.py::load_config"
RUN = "app/main.py::Runner.run"

def anchors(repo, text):
    return find_anchors(text, build_graph(repo.root).graph)

def test_code_like_tokens():
    assert is_code_like("parse_config")
    assert is_code_like("a.b")
    assert is_code_like("ConfigParser")
    assert not is_code_like("Runner")
    assert not is_code_like("crashes")

def test_backticked_name_resolves(repo):
    assert anchors(repo, "The function `parse_config` crashes on empty input.").anchors == [PARSE]

def test_plain_code_like_name_and_path_resolve(repo):
    result = anchors(repo, "load_config in app/config.py fails.")
    assert result.anchors == ["app/config.py", LOAD]

def test_plain_words_are_not_anchors(repo):
    result = anchors(repo, "The run command crashes and Runner is slow.")
    assert result.anchors == []
    assert result.unresolved == []

def test_ambiguous_backticked_name_is_reported_not_anchored(repo):
    result = anchors(repo, "Calling `run` fails.")
    assert result.anchors == []
    assert result.ambiguous == ["run"]

def test_call_parentheses_and_qualified_names(repo):
    assert anchors(repo, "`Runner.run()` returns the wrong value").anchors == [RUN]

def test_module_prefixed_name_falls_back_to_the_function(repo):
    assert anchors(repo, "see config.parse_config").anchors == [PARSE]

def test_unknown_name_is_unresolved(repo):
    result = anchors(repo, "`nonexistent_function` is missing")
    assert result.unresolved == ["nonexistent_function"]

def test_traceback_in_fenced_block(repo):
    text = 'Traceback:\n```\nFile "/site/pkg/app/config.py", line 5, in parse_config\n```\n'
    assert anchors(repo, text).anchors == ["app/config.py", PARSE]

def test_tokens_are_deduplicated():
    tokens = extract_tokens("`foo_bar` and foo_bar and `foo_bar`")
    assert [token for token, _ in tokens] == ["foo_bar"]

def build(tmp_path, files):
    for relative, text in files.items():
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
    return build_graph(tmp_path).graph

def test_symbols_defined_only_in_test_files_are_not_anchors(tmp_path):
    graph = build(
        tmp_path,
        {
            "pkg/core.py": "def work():\n    pass\n",
            "tests/test_core.py": "class CityInline:\n    pass\n",
        },
    )
    result = find_anchors("The `CityInline` admin crashes", graph)
    assert result.anchors == []
    assert result.unresolved == ["CityInline"]

def test_testing_directories_and_conftest_are_excluded(tmp_path):
    graph = build(
        tmp_path,
        {
            "pkg/testing/path.py": "class path:\n    def abspath(self):\n        pass\n",
            "conftest.py": "def fixture_helper():\n    pass\n",
        },
    )
    assert find_anchors("see `path.abspath` and `fixture_helper`", graph).anchors == []

def test_test_file_paths_are_not_anchors(tmp_path):
    graph = build(tmp_path, {"pkg/core.py": "x = 1\n", "tests/test_core.py": "y = 2\n"})
    assert find_anchors("see tests/test_core.py and pkg/core.py", graph).anchors == ["pkg/core.py"]

def test_stdlib_dotted_references_are_skipped(repo):
    result = anchors(repo, "calls `os.path.load_config` somewhere")
    assert result.anchors == []
    assert result.unresolved == []

def test_variable_receiver_falls_back_to_the_method_name(repo):
    assert anchors(repo, "after `x.parse_config` the value is wrong").anchors == [PARSE]

def test_docs_and_examples_are_excluded(tmp_path):
    graph = build(
        tmp_path,
        {
            "pkg/core.py": "x = 1\n",
            "doc/conf.py": "def setup():\n    pass\n",
            "examples/demo.py": "def demo_run():\n    pass\n",
        },
    )
    result = find_anchors("see doc/conf.py and `demo_run` and `setup`", graph)
    assert result.anchors == []

def test_bare_filenames_are_not_anchors(tmp_path):
    graph = build(tmp_path, {"pkg/core.py": "x = 1\n"})
    assert find_anchors("core.py fails", graph).anchors == []
    assert find_anchors("pkg/core.py fails", graph).anchors == ["pkg/core.py"]