import re

from pydantic import BaseModel, Field

from swe_struct.graph.model import CodeGraph, NodeKind

HUNK_HEADER = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")

class FileChange(BaseModel):
    path: str
    removed: list[int] = Field(default_factory=list)
    insertions: list[tuple[int, int]] = Field(default_factory=list)

def strip_prefix(path: str) -> str:
    path = path.split("\t")[0].strip()
    return path[2:] if path.startswith(("a/", "b/")) else path

def parse_patch(text: str) -> list[FileChange]:
    changes: list[FileChange] = []
    current: FileChange | None = None
    old_line = 0
    remaining_old = 0
    remaining_new = 0
    previous = " "
    for line in text.splitlines():
        if remaining_old > 0 or remaining_new > 0:
            marker = line[:1]
            if marker == "\\":
                continue
            if marker == "-":
                if current is not None:
                    current.removed.append(old_line)
                old_line += 1
                remaining_old -= 1
                previous = "-"
            elif marker == "+":
                if current is not None and previous == " ":
                    current.insertions.append((old_line - 1, old_line))
                remaining_new -= 1
                previous = "+" if previous != "-" else "-"
            else:
                old_line += 1
                remaining_old -= 1
                remaining_new -= 1
                previous = " "
            continue
        if line.startswith("diff --git"):
            current = None
        elif line.startswith("--- "):
            old_path = line[4:].split("\t")[0].strip()
            if old_path == "/dev/null":
                current = None
            else:
                current = FileChange(path=strip_prefix(old_path))
                changes.append(current)
        else:
            match = HUNK_HEADER.match(line)
            if match:
                start = int(match.group(1))
                old_count = int(match.group(2)) if match.group(2) is not None else 1
                new_count = int(match.group(4)) if match.group(4) is not None else 1
                old_line = start + 1 if old_count == 0 else start
                remaining_old = old_count
                remaining_new = new_count
                previous = " "
    return changes

class SpanIndex:
    def __init__(self, graph: CodeGraph) -> None:
        self._spans: dict[str, list[tuple[int, int, int, str]]] = {}
        for node in graph.nodes.values():
            if node.kind == NodeKind.FILE or node.start_line is None or node.end_line is None:
                continue
            rank = 0 if node.kind == NodeKind.FUNCTION else 1
            self._spans.setdefault(node.path, []).append((node.start_line, node.end_line, rank, node.id))

    def locate(self, path: str, first: int, last: int) -> str | None:
        containing = [
            span for span in self._spans.get(path, []) if span[0] <= first and last <= span[1]
        ]
        if not containing:
            return None
        best = min(containing, key=lambda span: (span[1] - span[0], span[2], span[3]))
        return best[3]

def patched_nodes(graph: CodeGraph, changes: list[FileChange]) -> list[str]:
    index = SpanIndex(graph)
    found: set[str] = set()
    for change in changes:
        if change.path not in graph.nodes:
            continue
        for line in change.removed:
            found.add(index.locate(change.path, line, line) or change.path)
        for before, after in change.insertions:
            owner = index.locate(change.path, before, after) if before >= 1 else None
            found.add(owner or change.path)
    return sorted(found)