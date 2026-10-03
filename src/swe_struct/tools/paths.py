import os
from collections.abc import Iterator
from pathlib import Path

IGNORED_DIRS = frozenset(
    {".git", ".hg", ".svn", "__pycache__", "node_modules", ".venv", ".tox", ".mypy_cache", ".pytest_cache"}
)
MAX_FILE_BYTES = 1_000_000
BINARY_SNIFF_BYTES = 2048

def resolve_inside(root: Path, relative: str) -> Path | None:
    base = root.resolve()
    candidate = (base / relative).resolve()
    if candidate == base or base in candidate.parents:
        return candidate
    return None

def relative_posix(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()

def iter_files(base: Path) -> Iterator[Path]:
    if base.is_file():
        yield base
        return
    for directory, dirnames, filenames in os.walk(base):
        dirnames[:] = sorted(name for name in dirnames if name not in IGNORED_DIRS)
        for filename in sorted(filenames):
            yield Path(directory) / filename

def is_searchable(path: Path) -> bool:
    if path.stat().st_size > MAX_FILE_BYTES:
        return False
    with path.open("rb") as handle:
        return b"\0" not in handle.read(BINARY_SNIFF_BYTES)