from swe_struct.data.selection import read_all_surveys, select_for_survey
from swe_struct.data.survey import TaskSurvey, append_survey
from swe_struct.data.tasks import Task

def make_tasks() -> list[Task]:
    tasks = []
    for repo, count in (("a/a", 10), ("b/b", 3)):
        for index in range(count):
            tasks.append(
                Task(
                    instance_id=f"{repo.replace('/', '__')}-{index}",
                    repo=repo,
                    base_commit="c",
                    problem_statement="p",
                    patch="",
                )
            )
    return tasks

def test_cap_counts_tasks_already_done():
    tasks = make_tasks()
    done = {"a__a-0", "a__a-1", "a__a-2", "a__a-3"}
    chosen = select_for_survey(tasks, done, [], per_repo=6, seed=0)
    repos = [task.repo for task in chosen]
    assert repos.count("a/a") == 2
    assert repos.count("b/b") == 3
    assert not done & {task.instance_id for task in chosen}

def test_no_cap_selects_everything_not_done():
    chosen = select_for_survey(make_tasks(), {"a__a-0"}, [], per_repo=0, seed=0)
    assert len(chosen) == 12

def test_repo_filter_and_determinism():
    first = select_for_survey(make_tasks(), set(), ["b/b"], per_repo=2, seed=1)
    again = select_for_survey(make_tasks(), set(), ["b/b"], per_repo=2, seed=1)
    assert [task.instance_id for task in first] == [task.instance_id for task in again]
    assert {task.repo for task in first} == {"b/b"}
    assert len(first) == 2

def test_limit_applies_after_selection():
    chosen = select_for_survey(make_tasks(), set(), [], per_repo=0, seed=0, limit=5)
    assert len(chosen) == 5

def test_read_all_surveys_merges_files_and_prefers_successes(tmp_path):
    task = make_tasks()[0]
    failed = TaskSurvey.failed(task, "boom")
    good = TaskSurvey(instance_id=task.instance_id, repo=task.repo, bucket_all="0-1")
    other = make_tasks()[1]
    append_survey(tmp_path / "survey.jsonl", failed)
    append_survey(tmp_path / "survey_w1.jsonl", good)
    append_survey(tmp_path / "survey_w2.jsonl", TaskSurvey(instance_id=other.instance_id, repo=other.repo, bucket_all="2"))
    merged = read_all_surveys(tmp_path)
    assert [survey.instance_id for survey in merged] == [task.instance_id, other.instance_id]
    assert merged[0].error is None