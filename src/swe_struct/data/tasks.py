from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel

DEFAULT_DATASET = "princeton-nlp/SWE-bench_Verified"

class Task(BaseModel):
    instance_id: str
    repo: str
    base_commit: str
    problem_statement: str
    patch: str

def task_from_row(row: Mapping[str, Any]) -> Task:
    return Task(
        instance_id=row["instance_id"],
        repo=row["repo"],
        base_commit=row["base_commit"],
        problem_statement=row["problem_statement"],
        patch=row["patch"],
    )

def load_swebench(dataset: str = DEFAULT_DATASET, split: str = "test") -> list[Task]:
    from datasets import load_dataset

    return [task_from_row(row) for row in load_dataset(dataset, split=split)]