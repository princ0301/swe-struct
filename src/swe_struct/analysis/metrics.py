from collections import defaultdict

from pydantic import BaseModel

from swe_struct.analysis.stats import wilson_interval
from swe_struct.core.schema import RunRecord
from swe_struct.data.audit import stratum_of
from swe_struct.data.survey import TaskSurvey

GRAPH_TOOL = "graph_neighbors"

class RunMetrics(BaseModel):
    run_id: str
    task_id: str
    repo: str
    arm: str
    model: str
    seed: int
    stratum: str
    stop_reason: str
    submitted: bool
    adopted: bool
    graph_calls: int
    first_graph_step: int | None
    steps: int
    tool_calls: int
    tokens: int
    file_recall: float
    file_precision: float | None
    function_recall_exact: float | None
    function_recall_lenient: float | None
    function_precision_lenient: float | None

def clean(item: str) -> str:
    return item.strip().replace("\\", "/").removeprefix("./")

def function_match(gold: str, submitted: str, lenient: bool) -> bool:
    gold_path, gold_qualified = gold.split("::", 1)
    has_path = "::" in submitted
    if has_path:
        submitted_path, submitted_qualified = submitted.split("::", 1)
        if submitted_path != gold_path:
            return False
    else:
        submitted_qualified = submitted
    if gold_qualified == submitted_qualified:
        return True
    if not has_path and gold_qualified.endswith("." + submitted_qualified):
        return True
    return lenient and (
        gold_qualified.startswith(submitted_qualified + ".")
        or submitted_qualified.startswith(gold_qualified + ".")
    )

def ratio(hits: int, total: int) -> float | None:
    return hits / total if total else None

def compute_run_metrics(record: RunRecord, survey: TaskSurvey) -> RunMetrics:
    events = [(step.index, event) for step in record.steps for event in step.tool_events]
    graph_steps = [index for index, event in events if event.name == GRAPH_TOOL]
    submission = record.submission or {}
    files = {clean(item) for item in submission.get("files", [])}
    functions = [clean(item) for item in submission.get("functions", [])]
    gold_files = {target.split("::", 1)[0] for target in survey.targets}
    gold_functions = [target for target in survey.targets if "::" in target]
    submitted = record.submission is not None
    exact = sum(1 for gold in gold_functions if any(function_match(gold, f, False) for f in functions))
    lenient = sum(1 for gold in gold_functions if any(function_match(gold, f, True) for f in functions))
    precise = sum(1 for f in functions if any(function_match(gold, f, True) for gold in gold_functions))
    return RunMetrics(
        run_id=record.run_id,
        task_id=record.task_id,
        repo=survey.repo,
        arm=record.arm,
        model=record.model,
        seed=record.seed,
        stratum=stratum_of(survey) or "unknown",
        stop_reason=record.stop_reason,
        submitted=submitted,
        adopted=bool(graph_steps),
        graph_calls=len(graph_steps),
        first_graph_step=min(graph_steps) if graph_steps else None,
        steps=len(record.steps),
        tool_calls=len(events),
        tokens=sum(step.prompt_tokens + step.completion_tokens for step in record.steps),
        file_recall=len(gold_files & files) / len(gold_files) if gold_files else 0.0,
        file_precision=ratio(len(gold_files & files), len(files)),
        function_recall_exact=(exact / len(gold_functions) if gold_functions else None),
        function_recall_lenient=(lenient / len(gold_functions) if gold_functions else None),
        function_precision_lenient=ratio(precise, len(functions)),
    )

def mean(values: list[float | None]) -> float | None:
    present = [value for value in values if value is not None]
    return sum(present) / len(present) if present else None

def fmt(value: float | None) -> str:
    return "  n/a" if value is None else f"{value:5.2f}"

def summarize_metrics(metrics: list[RunMetrics]) -> str:
    if not metrics:
        return "no runs"
    groups: dict[tuple[str, str], list[RunMetrics]] = defaultdict(list)
    for item in metrics:
        groups[(item.arm, item.stratum)].append(item)
    lines = [
        "arm stratum     n  submitted  adoption (95% interval)   steps  tokens  file_rec  func_rec  func_rec_len"
    ]
    for (arm, stratum), group in sorted(groups.items()):
        adopted = sum(1 for item in group if item.adopted)
        low, high = wilson_interval(adopted, len(group))
        lines.append(
            f"{arm:<3} {stratum:<8}{len(group):>5}  "
            f"{sum(1 for item in group if item.submitted):>9}  "
            f"{adopted / len(group):5.2f} ({low:4.2f}-{high:4.2f})        "
            f"{sum(item.steps for item in group) / len(group):5.1f}  "
            f"{sum(item.tokens for item in group) / len(group):6.0f}  "
            f"{fmt(mean([item.file_recall for item in group]))}     "
            f"{fmt(mean([item.function_recall_exact for item in group]))}     "
            f"{fmt(mean([item.function_recall_lenient for item in group]))}"
        )
    return "\n".join(lines)