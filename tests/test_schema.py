from swe_struct.core.schema import (
    SCHEMA_VERSION,
    RunRecord,
    StepRecord,
    ToolEvent,
    append_run,
    completed_run_ids,
    read_runs,
)

def make_record(run_id: str) -> RunRecord:
    event = ToolEvent(name="echo", arguments={"text": "hi"}, ok=True, result_chars=2, truncated=False)
    step = StepRecord(
        index=0,
        prompt_tokens=10,
        completion_tokens=5,
        latency_s=0.1,
        finish_reason="tool_calls",
        tool_events=[event],
    )
    return RunRecord(
        run_id=run_id,
        task_id="task-1",
        arm="A1",
        model="e4b",
        seed=0,
        git_sha="deadbeef",
        config_hash="abc",
        stop_reason="submitted",
        steps=[step],
        submission={"files": ["a.py"], "functions": []},
    )

def test_round_trip(tmp_path):
    path = tmp_path / "runs.jsonl"
    append_run(path, make_record("r1"))
    append_run(path, make_record("r2"))
    records = read_runs(path)
    assert [record.run_id for record in records] == ["r1", "r2"]
    assert records[0].schema_version == SCHEMA_VERSION
    assert records[0].steps[0].tool_events[0].name == "echo"

def test_completed_run_ids(tmp_path):
    path = tmp_path / "runs.jsonl"
    assert completed_run_ids(path) == set()
    append_run(path, make_record("r1"))
    assert completed_run_ids(path) == {"r1"}