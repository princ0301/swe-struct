from pathlib import Path

import typer

from swe_struct.analysis.words import count_sections

LIMIT = 3000

def main(directory: Path = Path("paper/sections")) -> None:
    counts = count_sections(directory)
    for name, count in counts.items():
        typer.echo(f"{name:<28}{count:>6}")
    total = sum(counts.values())
    typer.echo(f"{'total':<28}{total:>6} of {LIMIT} ({LIMIT - total} left)")

if __name__ == "__main__":
    typer.run(main)