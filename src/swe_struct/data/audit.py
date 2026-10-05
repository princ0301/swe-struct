import csv
import io
import random

from pydantic import BaseModel

from swe_struct.analysis.stats import wilson_interval
from swe_struct.data.manifest import STRATA
from swe_struct.data.survey import TaskSurvey
from swe_struct.data.tasks import Task

EXCERPT_CHARS = 700
VERDICTS = ("correct", "partial", "wrong")
AUDITED_STRATA = ("far", "near")

class AuditScore(BaseModel):
    scored: int
    unscored: int
    correct: int
    partial: int
    wrong: int
    strict: float
    strict_interval: tuple[float, float]
    lenient: float
    lenient_interval: tuple[float, float]

def stratum_of(survey: TaskSurvey) -> str | None:
    for name, buckets in STRATA.items():
        if survey.bucket_all in buckets:
            return name
    return None

def pick_audit_sample(surveys: list[TaskSurvey], per_stratum: dict[str, int], seed: int) -> list[TaskSurvey]:
    picked: list[TaskSurvey] = []
    for stratum in AUDITED_STRATA:
        eligible = sorted(
            (
                survey
                for survey in surveys
                if survey.error is None and survey.anchors and stratum_of(survey) == stratum
            ),
            key=lambda survey: survey.instance_id,
        )
        count = min(per_stratum.get(stratum, 0), len(eligible))
        picked += random.Random(f"{seed}:{stratum}").sample(eligible, count)
    random.Random(seed).shuffle(picked)
    return picked

def render_audit_sheet(samples: list[TaskSurvey], tasks: dict[str, Task]) -> str:
    blocks = [
        "Mark each task: correct (the anchors are what the issue is about), "
        "partial (some are, some are not), wrong (none are). Record verdicts in the CSV file."
    ]
    for number, survey in enumerate(samples, start=1):
        excerpt = tasks[survey.instance_id].problem_statement[:EXCERPT_CHARS].replace("\n", "\n> ")
        blocks.append(
            f"## {number}. {survey.instance_id}\n"
            f"Anchors: {', '.join(survey.anchors)}\n"
            f"Patched targets: {', '.join(survey.targets)}\n"
            f"Issue (first {EXCERPT_CHARS} characters):\n> {excerpt}\n"
            "Verdict: ____"
        )
    return "\n\n".join(blocks) + "\n"

def verdict_template(samples: list[TaskSurvey]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["instance_id", "verdict", "note"])
    for survey in samples:
        writer.writerow([survey.instance_id, "", ""])
    return buffer.getvalue()

def score_rows(rows: list[tuple[str, str]]) -> AuditScore:
    counts = {verdict: 0 for verdict in VERDICTS}
    unscored = 0
    for _, verdict in rows:
        if verdict in counts:
            counts[verdict] += 1
        else:
            unscored += 1
    scored = sum(counts.values())
    lenient_hits = counts["correct"] + counts["partial"]
    return AuditScore(
        scored=scored,
        unscored=unscored,
        correct=counts["correct"],
        partial=counts["partial"],
        wrong=counts["wrong"],
        strict=counts["correct"] / scored if scored else 0.0,
        strict_interval=wilson_interval(counts["correct"], scored),
        lenient=lenient_hits / scored if scored else 0.0,
        lenient_interval=wilson_interval(lenient_hits, scored),
    )

def score_verdicts(text: str, strata: dict[str, str]) -> dict[str, AuditScore]:
    rows = [
        (row["instance_id"], (row.get("verdict") or "").strip().lower())
        for row in csv.DictReader(io.StringIO(text))
    ]
    scores = {"all": score_rows(rows)}
    for stratum in AUDITED_STRATA:
        scores[stratum] = score_rows([row for row in rows if strata.get(row[0]) == stratum])
    return scores