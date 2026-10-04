from swe_struct.data.survey import (
    TaskSurvey,
    append_survey,
    read_surveys,
    summarize,
    survey_task,
)
from swe_struct.data.tasks import Task, task_from_row

INSERT_IN_PARSE = (
    "--- a/app/config.py\n+++ b/app/config.py\n@@ -2,2 +2,3 @@\n"
    "     result = {}\n+    seen = set()\n     for line in text.splitlines():\n"
)
README_PATCH = "--- a/README.md\n+++ b/README.md\n@@ -1,1 +1,1 @@\n-a\n+b\n"

def make_task(problem: str, patch: str) -> Task:
    return Task(instance_id="t-1", repo="o/r", base_commit="abc", problem_statement=problem, patch=patch)

def test_anchor_inside_patched_function_is_close(repo):
    survey = survey_task(make_task("`parse_config` is broken", INSERT_IN_PARSE), repo.root)
    assert survey.patched == ["app/config.py::parse_config"]
    assert survey.distance_all == 0
    assert survey.bucket_all == "0-1"

def test_two_hops_through_calls(repo):
    survey = survey_task(make_task("`Runner.run` is broken", INSERT_IN_PARSE), repo.root)
    assert survey.distance_all == 2
    assert survey.bucket_all == "2"

def test_no_anchor(repo):
    survey = survey_task(make_task("It crashes.", INSERT_IN_PARSE), repo.root)
    assert survey.bucket_all == "no_anchor"

def test_no_target_when_patch_has_no_python_change(repo):
    survey = survey_task(make_task("`parse_config` is broken", README_PATCH), repo.root)
    assert survey.bucket_all == "no_target"

def test_task_from_row_ignores_extra_fields():
    row = {
        "instance_id": "a__b-1",
        "repo": "a/b",
        "base_commit": "deadbeef",
        "problem_statement": "text",
        "patch": "diff",
        "hints_text": "ignored",
    }
    assert task_from_row(row).instance_id == "a__b-1"

def test_survey_round_trip_and_summary(tmp_path, repo):
    path = tmp_path / "survey.jsonl"
    close = survey_task(make_task("`parse_config` is broken", INSERT_IN_PARSE), repo.root)
    far = survey_task(make_task("`Runner.run` is broken", INSERT_IN_PARSE), repo.root)
    failed = TaskSurvey.failed(make_task("x", "y"), "boom")
    for survey in (close, far, failed):
        append_survey(path, survey)
    surveys = read_surveys(path)
    assert len(surveys) == 3
    text = summarize(surveys)
    assert "tasks: 3, surveyed: 2, errors: 1" in text
    assert "0-1" in text
    assert "o/r" in text

def test_empty_summary():
    assert summarize([]) == "no tasks surveyed"

def test_file_level_targets_are_dropped_when_finer_ones_exist(repo):
    patch = (
        "--- a/app/config.py\n+++ b/app/config.py\n@@ -2,1 +2,1 @@\n-    result = {}\n+    result = dict()\n"
        "@@ -6,2 +6,3 @@\n     return result\n+# note\n \n"
    )
    survey = survey_task(make_task("`parse_config` is broken", patch), repo.root)
    assert survey.patched == ["app/config.py", "app/config.py::parse_config"]
    assert survey.targets == ["app/config.py::parse_config"]

def test_lexical_hit_requires_the_patched_name_in_the_issue(repo):
    named = survey_task(make_task("`parse_config` is broken", INSERT_IN_PARSE), repo.root)
    unnamed = survey_task(make_task("`Runner.run` is broken", INSERT_IN_PARSE), repo.root)
    assert named.lexical_hit
    assert not unnamed.lexical_hit

def test_short_plain_names_do_not_count_as_lexical_hits(repo):
    patch = "--- a/app/base.py\n+++ b/app/base.py\n@@ -3,1 +3,1 @@\n-        return None\n+        return 1\n"
    survey = survey_task(make_task("`Runner.run` fails when we run it", patch), repo.root)
    assert survey.targets == ["app/base.py::Base.run"]
    assert not survey.lexical_hit