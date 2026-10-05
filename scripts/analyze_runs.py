from pathlib import Path

import typer

from swe_struct.analysis.metrics import compute_run_metrics, summarize_metrics
from swe_struct.core.schema import read_runs
from swe_struct.data.selection import read_all_surveys

def main(path: Path = Path("runs/logs/runs.jsonl"), survey_dir: Path = Path("runs")) -> None:
    surveys = {survey.instance_id: survey for survey in read_all_surveys(survey_dir)}
    records = [record for record in read_runs(path) if record.task_id in surveys]
    metrics = [compute_run_metrics(record, surveys[record.task_id]) for record in records]
    typer.echo(summarize_metrics(metrics))

if __name__ == "__main__":
    typer.run(main)