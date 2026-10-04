from pathlib import Path

import typer

from swe_struct.data.selection import read_all_surveys
from swe_struct.data.survey import summarize

def main(directory: Path = Path("runs")) -> None:
    typer.echo(summarize(read_all_surveys(directory)))

if __name__ == "__main__":
    typer.run(main)