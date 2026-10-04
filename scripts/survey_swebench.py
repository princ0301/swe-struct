import time
from pathlib import Path

import typer

from swe_struct.data.repos import GitError, RepoCache
from swe_struct.data.selection import read_all_surveys, select_for_survey
from swe_struct.data.survey import TaskSurvey, append_survey, summarize, survey_task
from swe_struct.data.tasks import DEFAULT_DATASET, load_swebench

def main(
    limit: int = 0,
    seed: int = 0,
    per_repo: int = 0,
    repos: str = "",
    cache_dir: Path = Path("data_cache"),
    output: Path = Path("runs/survey.jsonl"),
    dataset: str = DEFAULT_DATASET,
) -> None:
    done_ids = {survey.instance_id for survey in read_all_surveys(output.parent)}
    repo_list = [repo.strip() for repo in repos.split(",") if repo.strip()]
    tasks = select_for_survey(load_swebench(dataset), done_ids, repo_list, per_repo, seed, limit)
    cache = RepoCache(cache_dir)
    typer.echo(f"{len(tasks)} tasks to survey")
    for index, task in enumerate(tasks, start=1):
        started = time.perf_counter()
        checked = started
        try:
            root = cache.checkout_shared(task.repo, task.base_commit)
            checked = time.perf_counter()
            survey = survey_task(task, root)
        except (GitError, OSError) as error:
            survey = TaskSurvey.failed(task, str(error))
        finished = time.perf_counter()
        append_survey(output, survey)
        typer.echo(
            f"{index}/{len(tasks)} {task.instance_id} {survey.bucket_all} "
            f"checkout={checked - started:.0f}s survey={finished - checked:.0f}s"
        )
    typer.echo(summarize(read_all_surveys(output.parent)))

if __name__ == "__main__":
    typer.run(main)