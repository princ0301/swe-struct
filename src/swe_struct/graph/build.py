import ast
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from swe_struct.graph.model import CodeGraph, Edge, EdgeKind, Node, NodeKind
from swe_struct.tools.paths import is_searchable, iter_files, relative_posix

FunctionDef = ast.FunctionDef | ast.AsyncFunctionDef

class BuildStats(BaseModel):
    files: int = 0
    files_skipped: int = 0
    parse_failures: int = 0
    imports_internal: int = 0
    imports_external: int = 0
    calls_resolved: int = 0
    calls_dynamic: int = 0
    calls_external: int = 0

    def call_resolution_rate(self) -> float:
        resolvable = self.calls_resolved + self.calls_dynamic
        return self.calls_resolved / resolvable if resolvable else 0.0

class BuildResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    graph: CodeGraph
    stats: BuildStats

@dataclass
class _File:
    path: str
    tree: ast.Module
    top_level: dict[str, str] = field(default_factory=dict)
    symbols: dict[str, str] = field(default_factory=dict)
    modules: dict[str, str] = field(default_factory=dict)

@dataclass
class _FunctionSite:
    node_id: str
    node: FunctionDef
    class_id: str | None
    file: _File

def module_name(path: str) -> str:
    parts = path[: -len(".py")].split("/")
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)

def package_parts(path: str) -> list[str]:
    parts = path[: -len(".py")].split("/")
    return parts[:-1]

def nested_statements(node: ast.AST) -> Iterator[ast.stmt]:
    for child in ast.iter_child_nodes(node):
        if isinstance(child, ast.stmt):
            yield child
        elif isinstance(child, (ast.ExceptHandler, ast.match_case)):
            yield from nested_statements(child)

def calls_in(function: FunctionDef) -> Iterator[ast.Call]:
    stack: list[ast.AST] = list(function.body)
    while stack:
        node = stack.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if isinstance(node, ast.Call):
            yield node
        stack.extend(ast.iter_child_nodes(node))

class _Builder:
    def __init__(self) -> None:
        self.stats = BuildStats()
        self.nodes: dict[str, Node] = {}
        self.edges: set[tuple[str, str, EdgeKind]] = set()
        self.files: dict[str, _File] = {}
        self.sites: list[_FunctionSite] = []
        self.methods: dict[str, dict[str, str]] = {}
        self.bases: dict[str, list[str]] = {}
        self.exact: dict[str, str] = {}
        self.suffix: dict[str, str | None] = {}

    def add_edge(self, source: str, target: str, kind: EdgeKind) -> None:
        if source != target:
            self.edges.add((source, target, kind))

    def parse_files(self, root: Path) -> None:
        for file in iter_files(root):
            if file.suffix != ".py":
                continue
            relative = relative_posix(root, file)
            if not is_searchable(file):
                self.stats.files_skipped += 1
                continue
            self.stats.files += 1
            self.nodes[relative] = Node(id=relative, kind=NodeKind.FILE, path=relative)
            try:
                tree = ast.parse(file.read_text(encoding="utf-8", errors="replace"))
            except (SyntaxError, ValueError, RecursionError):
                self.stats.parse_failures += 1
                continue
            self.files[relative] = _File(path=relative, tree=tree)

    def index_modules(self) -> None:
        for path in sorted(self.nodes):
            if path.endswith(".py"):
                name = module_name(path)
                if name:
                    self.exact.setdefault(name, path)
        for path in sorted(self.nodes):
            if not path.endswith(".py") or not module_name(path):
                continue
            parts = module_name(path).split(".")
            for start in range(1, len(parts)):
                name = ".".join(parts[start:])
                if name in self.exact:
                    continue
                self.suffix[name] = None if name in self.suffix and self.suffix[name] != path else path

    def resolve_module(self, name: str) -> str | None:
        return self.exact.get(name) or self.suffix.get(name)

    def collect_definitions(self) -> None:
        for file in self.files.values():
            for statement in file.tree.body:
                self.visit(file, statement, file.path, "", None)

    def visit(
        self, file: _File, statement: ast.stmt, parent_id: str, prefix: str, class_id: str | None
    ) -> None:
        if not isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            for child in nested_statements(statement):
                self.visit(file, child, parent_id, prefix, class_id)
            return
        qualified = prefix + statement.name
        node_id = f"{file.path}::{qualified}"
        if node_id in self.nodes:
            return
        is_class = isinstance(statement, ast.ClassDef)
        first_line = min([statement.lineno] + [d.lineno for d in statement.decorator_list])
        self.nodes[node_id] = Node(
            id=node_id,
            kind=NodeKind.CLASS if is_class else NodeKind.FUNCTION,
            path=file.path,
            start_line=first_line,
            end_line=statement.end_lineno,
        )
        self.add_edge(parent_id, node_id, EdgeKind.CONTAINS)
        if parent_id == file.path:
            file.top_level.setdefault(statement.name, node_id)
        if parent_id in self.nodes and self.nodes[parent_id].kind == NodeKind.CLASS:
            self.methods.setdefault(parent_id, {}).setdefault(statement.name, node_id)
        if isinstance(statement, ast.ClassDef):
            self.bases[node_id] = []
            inner_class: str | None = node_id
        else:
            self.sites.append(_FunctionSite(node_id, statement, class_id, file))
            inner_class = class_id
        for child in statement.body:
            self.visit(file, child, node_id, qualified + ".", inner_class)

    def resolve_imports(self) -> None:
        for file in self.files.values():
            for node in ast.walk(file.tree):
                if isinstance(node, ast.Import):
                    self.handle_import(file, node)
                elif isinstance(node, ast.ImportFrom):
                    self.handle_import_from(file, node)

    def link_module(self, file: _File, target: str | None) -> bool:
        if target is None:
            self.stats.imports_external += 1
            return False
        self.stats.imports_internal += 1
        self.add_edge(file.path, target, EdgeKind.IMPORTS)
        return True

    def handle_import(self, file: _File, node: ast.Import) -> None:
        for alias in node.names:
            target = self.resolve_module(alias.name)
            if self.link_module(file, target) and target is not None:
                if alias.asname:
                    file.modules[alias.asname] = target
                elif "." not in alias.name:
                    file.modules[alias.name] = target

    def handle_import_from(self, file: _File, node: ast.ImportFrom) -> None:
        if node.level:
            package = package_parts(file.path)
            keep = len(package) - (node.level - 1)
            if keep < 0:
                return
            base_parts = package[:keep] + (node.module.split(".") if node.module else [])
            base = ".".join(base_parts)
        else:
            base = node.module or ""
        base_path = self.resolve_module(base) if base else None
        linked_base = False
        for alias in node.names:
            if alias.name == "*":
                continue
            local = alias.asname or alias.name
            submodule = self.resolve_module(f"{base}.{alias.name}" if base else alias.name)
            if submodule:
                self.link_module(file, submodule)
                file.modules[local] = submodule
                continue
            if base_path and not linked_base:
                linked_base = self.link_module(file, base_path)
            elif base_path is None:
                self.stats.imports_external += 1
            if base_path and base_path in self.files:
                target = self.files[base_path].top_level.get(alias.name)
                if target:
                    file.symbols[local] = target

    def lookup_name(self, file: _File, name: str) -> str | None:
        return file.top_level.get(name) or file.symbols.get(name)

    def resolve_class(self, file: _File, expression: ast.expr) -> str | None:
        target: str | None = None
        if isinstance(expression, ast.Name):
            target = self.lookup_name(file, expression.id)
        elif isinstance(expression, ast.Attribute) and isinstance(expression.value, ast.Name):
            module_path = file.modules.get(expression.value.id)
            if module_path and module_path in self.files:
                target = self.files[module_path].top_level.get(expression.attr)
        if target and self.nodes[target].kind == NodeKind.CLASS:
            return target
        return None

    def link_inheritance(self) -> None:
        for file in self.files.values():
            for node in ast.walk(file.tree):
                if not isinstance(node, ast.ClassDef):
                    continue
                class_id = self.find_class_id(file, node)
                if class_id is None:
                    continue
                for base in node.bases:
                    target = self.resolve_class(file, base)
                    if target:
                        self.bases[class_id].append(target)
                        self.add_edge(class_id, target, EdgeKind.INHERITS)

    def find_class_id(self, file: _File, node: ast.ClassDef) -> str | None:
        candidates = [
            node_id
            for node_id, item in self.nodes.items()
            if item.path == file.path
            and item.kind == NodeKind.CLASS
            and item.start_line is not None
            and item.start_line <= node.lineno <= (item.end_line or node.lineno)
            and node_id.rsplit("::", 1)[-1].split(".")[-1] == node.name
        ]
        return candidates[0] if len(candidates) == 1 else None

    def lookup_method(self, class_id: str, name: str, seen: set[str] | None = None) -> str | None:
        seen = seen or set()
        if class_id in seen:
            return None
        seen.add(class_id)
        found = self.methods.get(class_id, {}).get(name)
        if found:
            return found
        for base in self.bases.get(class_id, []):
            found = self.lookup_method(base, name, seen)
            if found:
                return found
        return None

    def resolve_call(self, site: _FunctionSite, call: ast.Call) -> tuple[str, str | None]:
        function = call.func
        file = site.file
        if isinstance(function, ast.Name):
            target = self.lookup_name(file, function.id)
            return ("resolved", target) if target else ("external", None)
        if isinstance(function, ast.Attribute) and isinstance(function.value, ast.Name):
            owner = function.value.id
            if owner in ("self", "cls") and site.class_id:
                method = self.lookup_method(site.class_id, function.attr)
                return ("resolved", method) if method else ("dynamic", None)
            module_path = file.modules.get(owner)
            if module_path and module_path in self.files:
                target = self.files[module_path].top_level.get(function.attr)
                return ("resolved", target) if target else ("external", None)
            owner_target = self.lookup_name(file, owner)
            if owner_target and self.nodes[owner_target].kind == NodeKind.CLASS:
                method = self.lookup_method(owner_target, function.attr)
                return ("resolved", method) if method else ("dynamic", None)
        return ("dynamic", None)

    def link_calls(self) -> None:
        for site in self.sites:
            for call in calls_in(site.node):
                status, target = self.resolve_call(site, call)
                if status == "resolved" and target:
                    self.stats.calls_resolved += 1
                    self.add_edge(site.node_id, target, EdgeKind.CALLS)
                elif status == "external":
                    self.stats.calls_external += 1
                else:
                    self.stats.calls_dynamic += 1

    def result(self) -> BuildResult:
        ordered = sorted(self.edges, key=lambda edge: (edge[0], edge[1], edge[2].value))
        edges = [Edge(source=s, target=t, kind=k) for s, t, k in ordered]
        return BuildResult(graph=CodeGraph(self.nodes.values(), edges), stats=self.stats)

def build_graph(root: Path) -> BuildResult:
    builder = _Builder()
    builder.parse_files(root)
    builder.index_modules()
    builder.collect_definitions()
    builder.resolve_imports()
    builder.link_inheritance()
    builder.link_calls()
    return builder.result()