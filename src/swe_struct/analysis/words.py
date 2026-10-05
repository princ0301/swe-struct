import re
from pathlib import Path

COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
PLACEHOLDER = re.compile(r"\[TODO[^\]]*\]")
WORD = re.compile(r"[A-Za-z0-9][A-Za-z0-9'_./-]*")

def count_words(text: str) -> int:
    text = PLACEHOLDER.sub(" ", COMMENT.sub(" ", text))
    return len(WORD.findall(text))

def count_sections(directory: Path) -> dict[str, int]:
    return {
        path.name: count_words(path.read_text(encoding="utf-8"))
        for path in sorted(directory.glob("*.md"))
    }