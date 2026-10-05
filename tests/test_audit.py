from swe_struct.data.audit import (
    EXCERPT_CHARS,
    pick_audit_sample,
    render_audit_sheet,
    score_verdicts,
    stratum_of,
    verdict_template,
)
from swe_struct.data.survey import TaskSurvey
from swe_struct.data.tasks import Task

def survey(index: int, bucket: str = "2", anchors: list[str] | None = None, error: str | None = None) -> TaskSurvey:
    return TaskSurvey(
        instance_id=f"r__r-{index}",
        repo="r/r",
        anchors=["a.py::f"] if anchors is None else anchors,
        targets=["b.py::g"],
        bucket_all=bucket,
        error=error,
    )

def task(index: int, text: str = "issue text") -> Task:
    return Task(instance_id=f"r__r-{index}", repo="r/r", base_commit="c", problem_statement=text, patch="")

def test_strata_follow_the_hop_buckets():
    assert stratum_of(survey(0, "0-1")) == "near"
    assert stratum_of(survey(0, "2")) == "far"
    assert stratum_of(survey(0, "3+")) == "far"
    assert stratum_of(survey(0, "no_anchor")) == "none"
    assert stratum_of(survey(0, "error")) is None

def test_sample_takes_requested_counts_per_stratum():
    surveys = [survey(i, "3+") for i in range(10)] + [survey(100 + i, "0-1") for i in range(10)]
    sample = pick_audit_sample(surveys, {"far": 4, "near": 3}, seed=0)
    assert sum(1 for s in sample if stratum_of(s) == "far") == 4
    assert sum(1 for s in sample if stratum_of(s) == "near") == 3

def test_sample_skips_errors_and_unanchored_tasks():
    surveys = [survey(0), survey(1, anchors=[]), survey(2, error="boom"), survey(3)]
    sample = pick_audit_sample(surveys, {"far": 10, "near": 10}, seed=0)
    assert sorted(s.instance_id for s in sample) == ["r__r-0", "r__r-3"]

def test_sample_is_seeded_and_mixed():
    surveys = [survey(i, "3+") for i in range(10)] + [survey(100 + i, "0-1") for i in range(10)]
    first = pick_audit_sample(surveys, {"far": 5, "near": 5}, seed=1)
    again = pick_audit_sample(surveys, {"far": 5, "near": 5}, seed=1)
    assert [s.instance_id for s in first] == [s.instance_id for s in again]
    strata = [stratum_of(s) for s in first]
    assert strata != sorted(strata)

def test_sheet_hides_the_bucket_and_truncates_the_issue():
    text = "Q" * (EXCERPT_CHARS + 100)
    sheet = render_audit_sheet([survey(0)], {"r__r-0": task(0, text)})
    assert "Anchors: a.py::f" in sheet
    assert "Patched targets: b.py::g" in sheet
    assert "Bucket" not in sheet
    assert sheet.count("Q") == EXCERPT_CHARS

def test_template_has_one_row_per_task():
    template = verdict_template([survey(0), survey(1)])
    assert template.splitlines() == ["instance_id,verdict,note", "r__r-0,,", "r__r-1,,"]

def test_scoring_overall_and_per_stratum():
    text = "instance_id,verdict,note\na,correct,\nb,Partial,\nc,wrong,\nd,correct,\ne,,\n"
    strata = {"a": "far", "b": "far", "c": "near", "d": "near", "e": "near"}
    scores = score_verdicts(text, strata)
    assert (scores["all"].scored, scores["all"].unscored) == (4, 1)
    assert scores["all"].strict == 0.5
    assert scores["all"].lenient == 0.75
    assert (scores["far"].correct, scores["far"].partial, scores["far"].scored) == (1, 1, 2)
    assert (scores["near"].correct, scores["near"].wrong, scores["near"].unscored) == (1, 1, 1)

def test_scoring_an_empty_sheet():
    scores = score_verdicts("instance_id,verdict,note\n", {})
    assert scores["all"].scored == 0
    assert scores["far"].strict == 0.0