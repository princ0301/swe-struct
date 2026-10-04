from collections import Counter
from pathlib import Path

import typer

from swe_struct.core.schema import read_runs


def main(path: Path = Path("runs/logs/runs.jsonl")) -> None:
    for record in read_runs(path):
        tools = Counter(event.name for step in record.steps for event in step.tool_events)
        tokens = sum(step.prompt_tokens + step.completion_tokens for step in record.steps)
        typer.echo(
            f"{record.task_id} {record.arm} seed={record.seed} stop={record.stop_reason} "
            f"steps={len(record.steps)} tokens={tokens} tools={dict(tools)}"
        )
        if record.submission:
            typer.echo(f"  submitted: {record.submission}")


if __name__ == "__main__":
    typer.run(main)