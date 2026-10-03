from swe_struct.tools.view_file import ViewFileTool

def test_default_view_is_numbered(repo):
    content = ViewFileTool()(repo, path="app/config.py").content
    assert content.startswith("app/config.py lines 1-10 of 10\n1: def parse_config(text):")

def test_range(repo):
    content = ViewFileTool()(repo, path="app/config.py", start_line=8, end_line=9).content
    assert content == "app/config.py lines 8-9 of 10\n8: def load_config(path):\n9:     with open(path) as handle:"

def test_end_is_clamped_to_file_length(repo):
    content = ViewFileTool()(repo, path="app/base.py", start_line=2, end_line=99).content
    assert content.startswith("app/base.py lines 2-3 of 3")

def test_missing_file(repo):
    assert not ViewFileTool()(repo, path="app/nope.py").ok

def test_escape_is_rejected(repo):
    assert not ViewFileTool()(repo, path="../../conftest.py").ok

def test_start_beyond_end_of_file(repo):
    assert not ViewFileTool()(repo, path="app/base.py", start_line=50).ok

def test_inverted_range(repo):
    assert not ViewFileTool()(repo, path="app/config.py", start_line=5, end_line=2).ok