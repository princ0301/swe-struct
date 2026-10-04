from pathlib import Path

from swe_struct.agent.arms import ArmConfig
from swe_struct.core.types import RepoContext
from swe_struct.graph.model import CodeGraph, NodeKind
from swe_struct.tools.graph_neighbors import GraphNeighborsTool

PROMPT_VERSION = "v1"
MAX_ISSUE_CHARS = 12000
MAX_HINT_ANCHORS = 5
MAX_HINT_LINES = 40
MAX_BLOCK_LINES = 15
SYSTEM_PROMPT = (
    "You are an expert software engineer working on a Python repository. "
    "You are given a bug report. Your job is to find the code that must change to fix it. "
    "Explore the repository with the tools provided, then call submit with the files and the functions "
    "or methods that need to be edited, written as path/to/file.py::Class.method or path/to/file.py::function. "
    "Do not write a patch. Call submit once, when you are confident."
)
REMINDER = "Before you submit, check the neighbors of the symbols you intend to name with graph_neighbors."

def render_hints(graph: CodeGraph, anchors: list[str]) -> str | None:
    tool = GraphNeighborsTool(graph)
    context = RepoContext(root=Path("."))
    ordered = sorted(anchors, key=lambda anchor: (graph.nodes[anchor].kind == NodeKind.FILE, anchor))
    blocks: list[str] = []
    used = 0
    for anchor in ordered[:MAX_HINT_ANCHORS]:
        result = tool(context, symbol=anchor, direction="both", hops=1)
        lines = result.content.splitlines()
        if not result.ok or len(lines) < 2:
            continue
        room = min(MAX_BLOCK_LINES, MAX_HINT_LINES - used)
        if room <= 0:
            break
        blocks.append("\n".join(lines[:room]))
        used += min(len(lines), room)
    return "\n\n".join(blocks) or None

def build_user_prompt(problem: str, arm: ArmConfig, hints: str | None) -> str:
    parts = [f"Bug report:\n{problem[:MAX_ISSUE_CHARS]}"]
    if hints:
        parts.append(f"Repository structure hints:\n{hints}")
    parts.append("Locate the code that needs to change, then call submit.")
    if arm.reminder:
        parts.append(REMINDER)
    return "\n\n".join(parts)