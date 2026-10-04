from swe_struct.core.types import RepoContext, ToolResult, ToolSpec

class SubmitTool:
    spec = ToolSpec(
        name="submit",
        description="Submit the final answer: the files and functions that must change to resolve the issue.",
        parameters={
            "type": "object",
            "properties": {
                "files": {"type": "array", "items": {"type": "string"}},
                "functions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Use the form path/to/file.py::Class.method or path/to/file.py::function.",
                },
            },
            "required": ["files"],
        },
    )

    def __call__(
        self, ctx: RepoContext, files: list[str], functions: list[str] | None = None
    ) -> ToolResult:
        data = {"files": list(files), "functions": list(functions or [])}
        return ToolResult(content="submitted", final=True, data=data)