import re

from swe_struct.core.types import RepoContext, ToolResult, ToolSpec
from swe_struct.tools.paths import is_searchable, iter_files, relative_posix, resolve_inside

MAX_LINE_CHARS = 200
DEFAULT_MAX_RESULTS = 50

class SearchTextTool:
    spec = ToolSpec(
        name="search_text",
        description="Search file contents with a regular expression. Returns path:line: text for each match.",
        parameters={
            "type": "object",
            "properties": {
                "pattern": {"type": "string"},
                "path": {"type": "string", "description": "File or directory to search, relative to the repository root."},
                "ignore_case": {"type": "boolean"},
                "max_results": {"type": "integer"},
            },
            "required": ["pattern"],
        },
    )

    def __call__(
        self,
        ctx: RepoContext,
        pattern: str,
        path: str = ".",
        ignore_case: bool = False,
        max_results: int = DEFAULT_MAX_RESULTS,
    ) -> ToolResult:
        target = resolve_inside(ctx.root, path)
        if target is None or not target.exists():
            return ToolResult(content=f"path not found: {path}", ok=False)
        try:
            regex = re.compile(pattern, re.IGNORECASE if ignore_case else 0)
        except re.error as error:
            return ToolResult(content=f"invalid pattern: {error}", ok=False)
        shown: list[str] = []
        total = 0
        for file in iter_files(target):
            if not is_searchable(file):
                continue
            text = file.read_text(encoding="utf-8", errors="replace")
            for number, line in enumerate(text.splitlines(), start=1):
                if not regex.search(line):
                    continue
                total += 1
                if len(shown) < max_results:
                    location = relative_posix(ctx.root, file)
                    shown.append(f"{location}:{number}: {line.strip()[:MAX_LINE_CHARS]}")
        if not shown:
            return ToolResult(content="no matches")
        hidden = total - len(shown)
        suffix = f"\n({hidden} more matches not shown)" if hidden else ""
        return ToolResult(content="\n".join(shown) + suffix)