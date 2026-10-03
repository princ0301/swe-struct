from swe_struct.core.types import RepoContext, ToolResult, ToolSpec
from swe_struct.tools.paths import resolve_inside

DEFAULT_WINDOW = 200

class ViewFileTool:
    spec = ToolSpec(
        name="view_file",
        description="Show numbered lines of a file. Shows the first 200 lines unless a range is given.",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "start_line": {"type": "integer"},
                "end_line": {"type": "integer"},
            },
            "required": ["path"],
        },
    )

    def __call__(
        self,
        ctx: RepoContext,
        path: str,
        start_line: int = 1,
        end_line: int | None = None,
    ) -> ToolResult:
        target = resolve_inside(ctx.root, path)
        if target is None or not target.is_file():
            return ToolResult(content=f"file not found: {path}", ok=False)
        lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
        total = len(lines)
        start = max(start_line, 1)
        end = min(end_line if end_line is not None else start + DEFAULT_WINDOW - 1, total)
        if start > total:
            return ToolResult(content=f"{path} has {total} lines", ok=False)
        if end < start:
            return ToolResult(content=f"invalid range: {start}-{end}", ok=False)
        body = "\n".join(f"{number}: {lines[number - 1]}" for number in range(start, end + 1))
        return ToolResult(content=f"{path} lines {start}-{end} of {total}\n{body}")