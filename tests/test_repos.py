import subprocess
from pathlib import Path

import pytest

from swe_struct.data.repos import GitError, RepoCache

def git(cwd: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()

@pytest.fixture
def origin(tmp_path):
    source = tmp_path / "origin" / "owner" / "name"
    source.mkdir(parents=True)
    git(source, "init", "-b", "main")
    (source / "f.txt").write_text("v1")
    git(source, "add", ".")
    git(source, "commit", "-m", "one")
    first = git(source, "rev-parse", "HEAD")
    (source / "f.txt").write_text("v2")
    git(source, "commit", "-am", "two")
    second = git(source, "rev-parse", "HEAD")
    cache = RepoCache(tmp_path / "cache", url_template=str(tmp_path / "origin") + "/{repo}")
    return cache, first, second

def test_checkout_two_commits(origin, tmp_path):
    cache, first, second = origin
    one = cache.checkout("owner/name", first, tmp_path / "work" / "one")
    two = cache.checkout("owner/name", second, tmp_path / "work" / "two")
    assert (one / "f.txt").read_text() == "v1"
    assert (two / "f.txt").read_text() == "v2"

def test_remove_deletes_the_checkout(origin, tmp_path):
    cache, first, _ = origin
    target = cache.checkout("owner/name", first, tmp_path / "work" / "one")
    cache.remove("owner/name", target)
    assert not target.exists()

def test_unknown_commit_raises(origin, tmp_path):
    cache, _, _ = origin
    with pytest.raises(GitError):
        cache.checkout("owner/name", "0" * 40, tmp_path / "work" / "x")

def test_mirror_is_reused(origin, tmp_path):
    cache, first, _ = origin
    cache.checkout("owner/name", first, tmp_path / "work" / "a")
    mirror = cache.mirror_path("owner/name")
    assert mirror.exists()
    assert cache.ensure_mirror("owner/name") == mirror

def test_current_git_sha_marks_dirty_trees(tmp_path):
    from swe_struct.data.repos import current_git_sha

    git(tmp_path, "init", "-b", "main")
    (tmp_path / "f.txt").write_text("a")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-m", "one")
    clean = current_git_sha(tmp_path)
    assert len(clean) == 40
    (tmp_path / "f.txt").write_text("b")
    assert current_git_sha(tmp_path) == clean + "-dirty"

def test_shared_checkout_moves_between_commits_in_one_directory(origin):
    cache, first, second = origin
    one = cache.checkout_shared("owner/name", first)
    assert (one / "f.txt").read_text() == "v1"
    two = cache.checkout_shared("owner/name", second)
    assert two == one
    assert (two / "f.txt").read_text() == "v2"
    back = cache.checkout_shared("owner/name", first)
    assert (back / "f.txt").read_text() == "v1"

def test_shared_checkout_recovers_from_a_broken_directory(origin):
    cache, first, second = origin
    shared = cache.checkout_shared("owner/name", first)
    (shared / ".git").unlink()
    again = cache.checkout_shared("owner/name", second)
    assert (again / "f.txt").read_text() == "v2"