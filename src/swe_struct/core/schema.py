from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

SCHEMA_VERSION = 1

class ToolEvent(BaseModel):
    name: str
    arguments: dict[str, Any]
    ok: bool
    result_chars: int
    truncated: bool

class StepRecord(BaseModel):
    index: int
    prompt_tokens: int
    completion_tokens: int
    latency_s: float
    finish_reason: str
    tool_events: list[ToolEvent] = Field(default_factory=list)

class RunRecord(BaseModel):
    schema_version: int = SCHEMA_VERSION
    run_id: str
    task_id: str
    arm: str
    model: str
    seed: int
    git_sha: str
    config_hash: str
    stop_reason: str
    steps: list[StepRecord]
    submission: dict[str, Any] | None = None

def append_run(path: Path, record: RunRecord) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(record.model_dump_json() + "\n")

def read_runs(path: Path) -> list[RunRecord]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as handle:
        return [RunRecord.model_validate_json(line) for line in handle if line.strip()]

def completed_run_ids(path: Path) -> set[str]:
    return {record.run_id for record in read_runs(path)}