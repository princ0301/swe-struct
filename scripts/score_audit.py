from pathlib import Path

import typer

from swe_struct.data.audit import AuditScore, score_verdicts, stratum_of
from swe_struct.data.selection import read_all_surveys

def show(name: str, score: AuditScore) -> None:
    typer.echo(f"{name}: scored {score.scored}, unscored {score.unscored}")
    typer.echo(f"  correct {score.correct}, partial {score.partial}, wrong {score.wrong}")
    low, high = score.strict_interval
    typer.echo(f"  strict precision {score.strict:.2f} (95% interval {low:.2f} to {high:.2f})")
    low, high = score.lenient_interval
    typer.echo(f"  lenient precision {score.lenient:.2f} (95% interval {low:.2f} to {high:.2f})")

def main(path: Path = Path("runs/audit_verdicts.csv"), directory: Path = Path("runs")) -> None:
    strata = {}
    for survey in read_all_surveys(directory):
        name = stratum_of(survey)
        if name:
            strata[survey.instance_id] = name
    for name, score in score_verdicts(path.read_text(encoding="utf-8-sig"), strata).items():
        show(name, score)

if __name__ == "__main__":
    typer.run(main)
