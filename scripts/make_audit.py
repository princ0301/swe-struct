from pathlib import Path

import typer

from swe_struct.data.audit import pick_audit_sample, render_audit_sheet, verdict_template
from swe_struct.data.selection import read_all_surveys
from swe_struct.data.tasks import DEFAULT_DATASET, load_swebench

def main(far: int = 20, near: int = 10, seed: int = 0, directory: Path = Path("runs")) -> None:
    samples = pick_audit_sample(read_all_surveys(directory), {"far": far, "near": near}, seed)
    tasks = {task.instance_id: task for task in load_swebench(DEFAULT_DATASET)}
    sheet = directory / "audit_sheet.md"
    verdicts = directory / "audit_verdicts.csv"
    sheet.write_text(render_audit_sheet(samples, tasks), encoding="utf-8", newline="\n")
    verdicts.write_text(verdict_template(samples), encoding="utf-8", newline="\n")
    typer.echo(f"wrote {sheet} and {verdicts} ({len(samples)} tasks)")

if __name__ == "__main__":
    typer.run(main)