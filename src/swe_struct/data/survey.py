import re
from collections import Counter
from pathlib import Path

from pydantic import BaseModel, Field

from swe_struct.data.anchors import find_anchors, is_code_like
from swe_struct.data.patch import parse_patch, patched_nodes
from swe_struct.data.tasks import Task
from swe_struct.graph.build import build_graph
from swe_struct.graph.hops import HopBucket, bucket_for, hop_distance
from swe_struct.graph.model import CodeGraph, NodeKind

NO_TARGET = "no_target"
ERROR = "error"
MIN_PLAIN_NAME_CHARS = 8
BUCKET_ORDER = [
    HopBucket.ZERO_OR_ONE.value,
    HopBucket.TWO.value,
    HopBucket.THREE_PLUS.value,
    HopBucket.DISCONNECTED.value,
    HopBucket.NO_ANCHOR.value,
    NO_TARGET,
    ERROR,
]

class TaskSurvey(BaseModel):
    instance_id: str
    repo: str
    error: str | None = None
    call_resolution_rate: float = 0.0
    anchors: list[str] = Field(default_factory=list)
    n_ambiguous: int = 0
    patched: list[str] = Field(default_factory=list)
    targets: list[str] = Field(default_factory=list)
    distance_all: int | None = None
    bucket_all: str = ERROR
    lexical_hit: bool = False

    @classmethod
    def failed(cls, task: Task, message: str) -> "TaskSurvey":
        return cls(instance_id=task.instance_id, repo=task.repo, error=message)

def label(has_anchor: bool, has_target: bool, distance: int | None) -> str:
    if not has_anchor:
        return HopBucket.NO_ANCHOR.value
    if not has_target:
        return NO_TARGET
    return bucket_for(True, distance).value

def lexical_hit(text: str, targets: list[str], graph: CodeGraph) -> bool:
    for target in targets:
        node = graph.nodes[target]
        if node.kind == NodeKind.FILE:
            if target in text or target.rsplit("/", 1)[-1] in text:
                return True
            continue
        name = target.split("::", 1)[-1].split(".")[-1]
        if name.startswith("__"):
            continue
        if not (is_code_like(name) or len(name) >= MIN_PLAIN_NAME_CHARS):
            continue
        if re.search(rf"\b{re.escape(name)}\b", text):
            return True
    return False

def survey_task(task: Task, root: Path, max_hops: int = 8) -> TaskSurvey:
    result = build_graph(root)
    graph = result.graph
    found = find_anchors(task.problem_statement, graph)
    patched = patched_nodes(graph, parse_patch(task.patch))
    fine = [node_id for node_id in patched if graph.nodes[node_id].kind != NodeKind.FILE]
    targets = fine or patched
    distance = hop_distance(graph, found.anchors, targets, max_hops)
    return TaskSurvey(
        instance_id=task.instance_id,
        repo=task.repo,
        call_resolution_rate=result.stats.call_resolution_rate(),
        anchors=found.anchors,
        n_ambiguous=len(found.ambiguous),
        patched=patched,
        targets=targets,
        distance_all=distance,
        bucket_all=label(bool(found.anchors), bool(targets), distance),
        lexical_hit=lexical_hit(task.problem_statement, targets, graph),
    )

def append_survey(path: Path, survey: TaskSurvey) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(survey.model_dump_json() + "\n")

def read_surveys(path: Path) -> list[TaskSurvey]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as handle:
        return [TaskSurvey.model_validate_json(line) for line in handle if line.strip()]

def summarize(surveys: list[TaskSurvey]) -> str:
    if not surveys:
        return "no tasks surveyed"
    total = len(surveys)
    ok = [s for s in surveys if s.error is None]
    with_anchor = sum(1 for s in ok if s.anchors)
    rates = [s.call_resolution_rate for s in ok]
    lines = [
        f"tasks: {total}, surveyed: {len(ok)}, errors: {total - len(ok)}",
        f"tasks with at least one anchor: {with_anchor} ({100 * with_anchor / max(len(ok), 1):.1f}%)",
        f"mean call resolution rate: {sum(rates) / max(len(rates), 1):.3f}",
        "hop bucket (all edge kinds)   n      %   name in issue",
    ]
    counts = Counter(s.bucket_all for s in surveys)
    explicit = Counter(s.bucket_all for s in surveys if s.lexical_hit)
    for name in BUCKET_ORDER:
        if counts[name]:
            share = 100 * counts[name] / total
            lines.append(f"  {name:<14}{counts[name]:>5} {share:5.1f}%  {explicit[name]:>5}")
    by_repo: dict[str, list[TaskSurvey]] = {}
    for survey in surveys:
        by_repo.setdefault(survey.repo, []).append(survey)
    lines.append("per repository (n, tasks in 2-hop or 3+ bucket)")
    for repo in sorted(by_repo):
        group = by_repo[repo]
        far = sum(1 for s in group if s.bucket_all in (HopBucket.TWO.value, HopBucket.THREE_PLUS.value))
        lines.append(f"  {repo:<32}{len(group):>4}{far:>4}")
    return "\n".join(lines)