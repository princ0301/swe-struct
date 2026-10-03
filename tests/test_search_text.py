from swe_struct.tools.search_text import SearchTextTool

def test_matches_use_posix_paths_and_line_numbers(repo):
    content = SearchTextTool()(repo, pattern="parse_config").content
    assert content.splitlines() == [
        "app/config.py:1: def parse_config(text):",
        "app/config.py:10: return parse_config(handle.read())",
    ]

def test_results_are_ordered_by_path(repo):
    content = SearchTextTool()(repo, pattern="load_config").content
    assert [line.split(": ")[0] for line in content.splitlines()] == [
        "app/config.py:8",
        "app/main.py:2",
        "app/main.py:6",
    ]

def test_path_restricts_the_search(repo):
    content = SearchTextTool()(repo, pattern="load_config", path="app/main.py").content
    assert "app/config.py" not in content

def test_ignore_case(repo):
    assert SearchTextTool()(repo, pattern="PARSE_CONFIG").content == "no matches"
    assert SearchTextTool()(repo, pattern="PARSE_CONFIG", ignore_case=True).ok

def test_invalid_pattern(repo):
    result = SearchTextTool()(repo, pattern="(")
    assert not result.ok
    assert "invalid pattern" in result.content

def test_result_cap_reports_hidden_matches(ctx):
    (ctx.root / "f.txt").write_text("hit\nhit\nhit\nhit\nhit\n")
    content = SearchTextTool()(ctx, pattern="hit", max_results=2).content
    assert len(content.splitlines()) == 3
    assert content.endswith("(3 more matches not shown)")

def test_binary_files_are_skipped(ctx):
    (ctx.root / "bin.dat").write_bytes(b"hit\0hit")
    (ctx.root / "text.txt").write_text("hit")
    assert SearchTextTool()(ctx, pattern="hit").content == "text.txt:1: hit"

def test_missing_path(repo):
    assert not SearchTextTool()(repo, pattern="x", path="nope").ok