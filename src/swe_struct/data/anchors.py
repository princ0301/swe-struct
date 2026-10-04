import re
import sys

from pydantic import BaseModel, Field

from swe_struct.graph.model import CodeGraph, NodeKind

FENCE = re.compile(r"```.*?```", re.DOTALL)
BACKTICK = re.compile(r"`([^`\n]+)`")
IDENT = re.compile(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*")
PATH = re.compile(r"[\w./-]+\.py\b")
CAMEL = re.compile(r"[A-Z][a-z0-9]+(?:[A-Z][a-z0-9]*)+")
MIN_TOKEN_CHARS = 3
SKIPPED_PREFIXES = ("self.", "cls.")
NON_SOURCE_DIRS = frozenset({"tests", "test", "testing", "doc", "docs", "examples", "benchmarks"})

class AnchorResult(BaseModel):
    anchors: list[str] = Field(default_factory=list)
    ambiguous: list[str] = Field(default_factory=list)
    unresolved: list[str] = Field(default_factory=list)

def is_code_like(token: str) -> bool:
    return "_" in token or "." in token or CAMEL.fullmatch(token) is not None

def is_non_source_path(path: str) -> bool:
    parts = path.split("/")
    name = parts[-1]
    return (
        any(part in NON_SOURCE_DIRS for part in parts[:-1])
        or name.startswith("test_")
        or name.endswith("_test.py")
        or name == "conftest.py"
    )

def is_stdlib_reference(token: str) -> bool:
    return "." in token and token.split(".")[0] in sys.stdlib_module_names

def extract_tokens(text: str) -> list[tuple[str, bool]]:
    fenced = FENCE.findall(text)
    rest = FENCE.sub(" ", text)
    found: dict[str, bool] = {}
    for span in BACKTICK.findall(rest):
        for token in IDENT.findall(span):
            found[token] = True
    plain = BACKTICK.sub(" ", rest)
    for block in [*fenced, plain]:
        for token in IDENT.findall(block):
            if is_code_like(token):
                found.setdefault(token, False)
    return [(token, ticked) for token, ticked in found.items() if len(token) >= MIN_TOKEN_CHARS]

def candidates(graph: CodeGraph, token: str, ticked: bool) -> list[str]:
    for prefix in SKIPPED_PREFIXES:
        if token.startswith(prefix):
            token = token[len(prefix) :]
    parts = token.split(".")
    options = [token]
    if len(parts) > 2:
        options.append(".".join(parts[-2:]))
    if len(parts) > 1 and (ticked or is_code_like(parts[-1])):
        options.append(parts[-1])
    return options

def visible_matches(graph: CodeGraph, query: str) -> list[str]:
    return [match for match in graph.find(query) if not is_non_source_path(graph.nodes[match].path)]

def resolve_path(graph: CodeGraph, token: str) -> list[str]:
    files = [
        node.id
        for node in graph.nodes.values()
        if node.kind == NodeKind.FILE and not is_non_source_path(node.id)
    ]
    if token in files:
        return [token]
    return sorted(
        file for file in files if token.endswith("/" + file) or file.endswith("/" + token)
    )

def find_anchors(text: str, graph: CodeGraph) -> AnchorResult:
    anchors: set[str] = set()
    ambiguous: set[str] = set()
    unresolved: set[str] = set()
    for token, ticked in extract_tokens(text):
        if is_stdlib_reference(token):
            continue
        for option in candidates(graph, token, ticked):
            matches = visible_matches(graph, option)
            if len(matches) == 1:
                anchors.add(matches[0])
                break
            if len(matches) > 1:
                ambiguous.add(token)
                break
        else:
            unresolved.add(token)
    for token in dict.fromkeys(PATH.findall(text)):
        if "/" not in token:
            continue
        matches = resolve_path(graph, token)
        if len(matches) == 1:
            anchors.add(matches[0])
        elif len(matches) > 1:
            ambiguous.add(token)
    return AnchorResult(
        anchors=sorted(anchors),
        ambiguous=sorted(ambiguous - anchors),
        unresolved=sorted(unresolved),
    )