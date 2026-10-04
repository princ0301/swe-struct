import random
from pathlib import Path

from swe_struct.data.survey import TaskSurvey, read_surveys
from swe_struct.data.tasks import Task

def select_for_survey(
    tasks: list[Task],
    done_ids: set[str],
    repos: list[str],
    per_repo: int,
    seed: int,
    limit: int = 0,
) -> list[Task]:
    by_repo: dict[str, list[Task]] = {}
    for task in tasks:
        if not repos or task.repo in repos:
            by_repo.setdefault(task.repo, []).append(task)
    chosen: list[Task] = []
    for repo in sorted(by_repo):
        group = sorted(by_repo[repo], key=lambda task: task.instance_id)
        pool = [task for task in group if task.instance_id not in done_ids]
        wanted = len(pool)
        if per_repo:
            already = len(group) - len(pool)
            wanted = min(len(pool), max(0, per_repo - already))
        chosen += random.Random(f"{seed}:{repo}").sample(pool, wanted)
    if limit and limit < len(chosen):
        chosen = random.Random(seed).sample(chosen, limit)
    return sorted(chosen, key=lambda task: task.instance_id)

def read_all_surveys(directory: Path, pattern: str = "survey*.jsonl") -> list[TaskSurvey]:
    latest: dict[str, TaskSurvey] = {}
    for path in sorted(directory.glob(pattern)):
        for survey in read_surveys(path):
            previous = latest.get(survey.instance_id)
            if previous is None or previous.error is not None or survey.error is None:
                latest[survey.instance_id] = survey
    return [latest[key] for key in sorted(latest)]