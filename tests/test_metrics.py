from swe_struct.analysis.metrics import (
    compute_run_metrics,
    function_match,
    summarize_metrics,
)
from swe_struct.core.schema import RunRecord, StepRecord, ToolEvent
from swe_struct.data.survey import TaskSurvey

GOLD = ["a.py::Foo.bar", "b.py::baz"]

def event(name: str) -> ToolEvent:
    return ToolEvent(name=name, arguments={}, ok=True, result_chars=1, truncated=False)

def step(index: int, *names: str) -> StepRecord:
    return StepRecord(
        index=index,
        prompt_tokens=10,
        completion_tokens=5,
        latency_s=0.1,
        finish_reason="tool_calls",
        tool_events=[event(name) for name in names],
    )

def record(steps, submission, arm="A2") -> RunRecord:
    return RunRecord(
        run_id="r",
        task_id="t",
        arm=arm,
        model="m",
        seed=0,
        git_sha="s",
        config_hash="c",
        stop_reason="submitted" if submission is not None else "max_steps",
        steps=steps,
        submission=submission,
    )

def survey(targets=None, bucket="3+") -> TaskSurvey:
    return TaskSurvey(
        instance_id="t",
        repo="r/r",
        targets=GOLD if targets is None else targets,
        bucket_all=bucket,
    )

def test_exact_and_bare_function_matching():
    assert function_match("a.py::Foo.bar", "a.py::Foo.bar", False)
    assert not function_match("a.py::Foo.bar", "b.py::Foo.bar", False)
    assert function_match("a.py::Foo.bar", "Foo.bar", False)
    assert function_match("a.py::Foo.bar", "bar", False)
    assert not function_match("a.py::Foo.bar", "a.py::Foo.baz", False)

def test_lenient_matching_links_classes_and_their_methods():
    assert function_match("a.py::Foo", "a.py::Foo.bar", True)
    assert function_match("a.py::Foo.bar", "a.py::Foo", True)
    assert not function_match("a.py::Foo", "a.py::Foo.bar", False)
    assert not function_match("a.py::Foo", "a.py::Foobar", True)

def test_adoption_and_first_graph_step():
    steps = [step(0, "search_text"), step(1, "graph_neighbors", "view_file"), step(2, "graph_neighbors"), step(3, "submit")]
    metrics = compute_run_metrics(record(steps, {"files": [], "functions": []}), survey())
    assert metrics.adopted
    assert metrics.graph_calls == 2
    assert metrics.first_graph_step == 1
    assert metrics.tool_calls == 5
    assert metrics.steps == 4
    assert metrics.tokens == 60

def test_no_graph_calls_means_no_adoption():
    metrics = compute_run_metrics(record([step(0, "view_file", "submit")], {"files": []}), survey())
    assert not metrics.adopted
    assert metrics.first_graph_step is None

def test_perfect_submission():
    submission = {"files": ["a.py", "b.py"], "functions": ["a.py::Foo.bar", "b.py::baz"]}
    metrics = compute_run_metrics(record([step(0, "submit")], submission), survey())
    assert metrics.file_recall == 1.0
    assert metrics.file_precision == 1.0
    assert metrics.function_recall_exact == 1.0
    assert metrics.function_precision_lenient == 1.0

def test_partial_submission_with_a_wrong_extra():
    submission = {"files": ["a.py", "z.py"], "functions": ["a.py::Foo.bar", "z.py::other"]}
    metrics = compute_run_metrics(record([step(0, "submit")], submission), survey())
    assert metrics.file_recall == 0.5
    assert metrics.file_precision == 0.5
    assert metrics.function_recall_exact == 0.5
    assert metrics.function_precision_lenient == 0.5

def test_lenient_recall_credits_the_class_level_answer():
    metrics = compute_run_metrics(
        record([step(0, "submit")], {"files": ["a.py"], "functions": ["a.py::Foo"]}),
        survey(targets=["a.py::Foo.bar"]),
    )
    assert metrics.function_recall_exact == 0.0
    assert metrics.function_recall_lenient == 1.0

def test_file_only_gold_has_no_function_metrics():
    metrics = compute_run_metrics(
        record([step(0, "submit")], {"files": ["a.py"], "functions": []}),
        survey(targets=["a.py"]),
    )
    assert metrics.file_recall == 1.0
    assert metrics.function_recall_exact is None

def test_a_run_without_submission_scores_zero_recall():
    metrics = compute_run_metrics(record([step(0, "view_file")], None), survey())
    assert not metrics.submitted
    assert metrics.file_recall == 0.0
    assert metrics.function_recall_exact == 0.0
    assert metrics.file_precision is None

def test_path_variants_are_normalized():
    submission = {"files": ["./a.py", "b.py"], "functions": ["a.py::Foo.bar"]}
    assert compute_run_metrics(record([step(0, "submit")], submission), survey()).file_recall == 1.0

def test_summary_table_groups_by_arm_and_stratum():
    hit = compute_run_metrics(
        record([step(0, "graph_neighbors"), step(1, "submit")], {"files": ["a.py"], "functions": ["a.py::Foo.bar"]}),
        survey(),
    )
    miss = compute_run_metrics(record([step(0, "submit")], {"files": [], "functions": []}), survey())
    text = summarize_metrics([hit, miss])
    assert "A2  far" in text
    assert "0.50" in text
    assert summarize_metrics([]) == "no runs"