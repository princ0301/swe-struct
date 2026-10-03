from swe_struct.tools.list_dir import ListDirTool

def test_root_listing(repo):
    assert ListDirTool()(repo).content == "app/"

def test_subdirectory_listing(repo):
    result = ListDirTool()(repo, path="app")
    assert result.content == "__init__.py\nbase.py\nconfig.py\nmain.py"

def test_missing_directory(repo):
    assert not ListDirTool()(repo, path="nope").ok

def test_escape_is_rejected(repo):
    assert not ListDirTool()(repo, path="../..").ok

def test_empty_directory(ctx):
    assert ListDirTool()(ctx).content == "(empty)"