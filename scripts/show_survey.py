from pathlib import Path

import typer

from swe_struct.data.anchors import extract_tokens
from swe_struct.data.survey import read_surveys
from swe_struct.data.tasks import DEFAULT_DATASET, load_swebench

SHOWN = 6

def main(path: Path = Path("runs/survey.jsonl"), bucket: str = "", limit: int = 0) -> None:
    surveys = read_surveys(path)
    if bucket:
        surveys = [survey for survey in surveys if survey.bucket_all == bucket]
    if limit:
        surveys = surveys[:limit]
    tasks = {task.instance_id: task for task in load_swebench(DEFAULT_DATASET)}
    for survey in surveys:
        typer.echo(
            f"{survey.instance_id} bucket={survey.bucket_all} distance={survey.distance_all} "
            f"name_in_issue={survey.lexical_hit}"
        )
        typer.echo(f"  anchors: {survey.anchors[:SHOWN]}")
        typer.echo(f"  patched: {survey.patched[:SHOWN]}")
        typer.echo(f"  targets: {survey.targets[:SHOWN]}")
        if survey.bucket_all == "no_anchor":
            tokens = [token for token, _ in extract_tokens(tasks[survey.instance_id].problem_statement)]
            typer.echo(f"  tokens: {tokens[:15]}")

if __name__ == "__main__":
    typer.run(main)