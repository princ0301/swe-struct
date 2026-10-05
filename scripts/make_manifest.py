from pathlib import Path

import typer

from swe_struct.data.manifest import select_experiment_tasks, write_manifest
from swe_struct.data.selection import read_all_surveys

def main(
    near: int = 10,
    far: int = 10,
    none: int = 10,
    max_per_repo: int = 4,
    seed: int = 0,
    name: str = "mve",
    directory: Path = Path("runs"),
    exclude_file: Path | None = None,
) -> None:
    excluded: set[str] = set()
    if exclude_file:
        excluded = {line.strip() for line in exclude_file.read_text().splitlines() if line.strip()}
    entries = select_experiment_tasks(
        read_all_surveys(directory),
        {"near": near, "far": far, "none": none},
        max_per_repo,
        seed,
        excluded,
    )
    manifests = Path("src/swe_struct/data/manifests")
    write_manifest(entries, manifests / f"{name}.json", Path(f"tasks_{name}.txt"))
    counts: dict[str, int] = {}
    for entry in entries:
        counts[entry.stratum] = counts.get(entry.stratum, 0) + 1
    typer.echo(f"wrote {len(entries)} tasks to {manifests / (name + '.json')} and tasks_{name}.txt {counts}")

if __name__ == "__main__":
    typer.run(main)