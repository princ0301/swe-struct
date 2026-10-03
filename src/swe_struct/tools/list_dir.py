from swe_struct.core.types import RepoContext, ToolResult, ToolSpec
from swe_struct.tools.paths import IGNORED_DIRS, resolve_inside

class ListDirTool:
    spec = ToolSpec(
        name="list_dir",
        description="List the entries of a directory. Directories end with a slash.",
        parameters={
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Directory relative to the repository root."}},
        },
    )

    def __call__(self, ctx: RepoContext, path: str = ".") -> ToolResult:
        target = resolve_inside(ctx.root, path)
        if target is None or not target.is_dir():
            return ToolResult(content=f"directory not found: {path}", ok=False)
        entries = sorted(target.iterdir(), key=lambda entry: (entry.is_file(), entry.name))
        names = [
            f"{entry.name}/" if entry.is_dir() else entry.name
            for entry in entries
            if entry.name not in IGNORED_DIRS
        ]
        return ToolResult(content="\n".join(names) or "(empty)")