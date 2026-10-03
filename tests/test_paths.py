from swe_struct.tools.paths import is_searchable, iter_files, relative_posix, resolve_inside

def test_resolve_inside_accepts_nested_path(tmp_path):
    (tmp_path / "a").mkdir()
    assert resolve_inside(tmp_path, "a") == (tmp_path / "a").resolve()

def test_resolve_inside_rejects_escape(tmp_path):
    assert resolve_inside(tmp_path, "..") is None
    assert resolve_inside(tmp_path, "../other") is None

def test_iter_files_is_sorted_and_skips_ignored(tmp_path):
    (tmp_path / "b.txt").write_text("b")
    (tmp_path / "a.txt").write_text("a")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("x")
    names = [relative_posix(tmp_path, path) for path in iter_files(tmp_path)]
    assert names == ["a.txt", "b.txt"]

def test_binary_and_large_files_are_not_searchable(tmp_path):
    binary = tmp_path / "bin.dat"
    binary.write_bytes(b"ab\0cd")
    text = tmp_path / "t.txt"
    text.write_text("hello")
    assert not is_searchable(binary)
    assert is_searchable(text)