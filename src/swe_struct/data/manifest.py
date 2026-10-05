import random
from itertools import zip_longest
from pathlib import Path

from pydantic import BaseModel

from swe_struct.data.survey import TaskSurvey

STRATA = {
    "near": frozenset({"0-1"}),
    "far": frozenset({"2", "3+"}),
    "none": frozenset({"no_anchor"}),
}

class ManifestEntry(BaseModel):
    instance_id: str
    repo: str
    stratum: str
    bucket: str
    distance: int | None
    lexical_hit: bool

def interleave_by_repo(group: list[TaskSurvey], rng: random.Random) -> list[TaskSurvey]:
    by_repo: dict[str, list[TaskSurvey]] = {}
    for survey in sorted(group, key=lambda survey: survey.instance_id):
        by_repo.setdefault(survey.repo, []).append(survey)
    queues = []
    for repo in sorted(by_repo):
        queue = list(by_repo[repo])
        rng.shuffle(queue)
        queues.append(queue)
    rng.shuffle(queues)
    return [item for row in zip_longest(*queues) for item in row if item is not None]

def select_experiment_tasks(
    surveys: list[TaskSurvey],
    per_stratum: dict[str, int],
    max_per_repo: int,
    seed: int,
    exclude: set[str] | None = None,
) -> list[ManifestEntry]:
    excluded = exclude or set()
    entries: list[ManifestEntry] = []
    for stratum, buckets in STRATA.items():
        pool = [
            survey
            for survey in surveys
            if survey.error is None and survey.bucket_all in buckets and survey.instance_id not in excluded
        ]
        used: dict[str, int] = {}
        picked = 0
        for survey in interleave_by_repo(pool, random.Random(f"{seed}:{stratum}")):
            if picked >= per_stratum.get(stratum, 0):
                break
            if used.get(survey.repo, 0) >= max_per_repo:
                continue
            used[survey.repo] = used.get(survey.repo, 0) + 1
            picked += 1
            entries.append(
                ManifestEntry(
                    instance_id=survey.instance_id,
                    repo=survey.repo,
                    stratum=stratum,
                    bucket=survey.bucket_all,
                    distance=survey.distance_all,
                    lexical_hit=survey.lexical_hit,
                )
            )
    return sorted(entries, key=lambda entry: (entry.stratum, entry.instance_id))

def write_manifest(entries: list[ManifestEntry], json_path: Path, ids_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        "[\n" + ",\n".join(entry.model_dump_json() for entry in entries) + "\n]\n", encoding="utf-8", newline="\n"
    )
    ids_path.write_text("".join(f"{entry.instance_id}\n" for entry in entries), encoding="ascii", newline="\n")