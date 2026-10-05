from swe_struct.analysis.words import count_sections, count_words

def test_plain_words():
    assert count_words("one two three") == 3

def test_comments_and_todo_markers_are_ignored():
    assert count_words("one <!-- hidden words here --> two [TODO: check this] three") == 3

def test_identifiers_count_as_single_words():
    assert count_words("call graph_neighbors on path/to/file.py now") == 5

def test_sections_are_counted_per_file(tmp_path):
    (tmp_path / "a.md").write_text("one two")
    (tmp_path / "b.md").write_text("three")
    (tmp_path / "skip.txt").write_text("ignored words")
    assert count_sections(tmp_path) == {"a.md": 2, "b.md": 1}