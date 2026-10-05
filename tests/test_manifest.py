from swe_struct.data.manifest import select_experiment_tasks, write_manifest
from swe_struct.data.survey import TaskSurvey

def make(repo: str, index: int, bucket: str) -> TaskSurvey:
    return TaskSurvey(instance_id=f"{repo}-{index}", repo=repo, bucket_all=bucket, distance_all=1)

def pool() -> list[TaskSurvey]:
    surveys = []
    for repo in ("a", "b", "c"):
        for index in range(6):
            surveys.append(make(repo, index, "0-1"))
            surveys.append(make(repo, 10 + index, "3+"))
            surveys.append(make(repo, 20 + index, "no_anchor"))
    surveys.append(make("a", 99, "2"))
    surveys.append(TaskSurvey.model_validate({"instance_id": "bad", "repo": "a", "error": "x"}))
    return surveys

def test_counts_per_stratum_and_repo_cap():
    entries = select_experiment_tasks(pool(), {"near": 6, "far": 6, "none": 3}, max_per_repo=2, seed=0)
    by_stratum: dict[str, list[str]] = {}
    for entry in entries:
        by_stratum.setdefault(entry.stratum, []).append(entry.repo)
    assert {key: len(value) for key, value in by_stratum.items()} == {"near": 6, "far": 6, "none": 3}
    for repos in by_stratum.values():
        assert max(repos.count(repo) for repo in set(repos)) <= 2

def test_selection_is_diverse_across_repos():
    entries = select_experiment_tasks(pool(), {"near": 3, "far": 0, "none": 0}, max_per_repo=5, seed=0)
    assert {entry.repo for entry in entries} == {"a", "b", "c"}

def test_deterministic_and_seed_sensitive():
    sizes = {"near": 4, "far": 4, "none": 4}
    first = select_experiment_tasks(pool(), sizes, 3, seed=1)
    again = select_experiment_tasks(pool(), sizes, 3, seed=1)
    other = select_experiment_tasks(pool(), sizes, 3, seed=2)
    assert first == again
    assert [e.instance_id for e in first] != [e.instance_id for e in other]

def test_exclusion_and_errors_are_respected():
    entries = select_experiment_tasks(pool(), {"near": 18, "far": 19, "none": 18}, 10, seed=0, exclude={"a-0"})
    ids = {entry.instance_id for entry in entries}
    assert "a-0" not in ids
    assert "bad" not in ids

def test_far_stratum_merges_two_hop_and_three_plus():
    entries = select_experiment_tasks(pool(), {"near": 0, "far": 19, "none": 0}, 10, seed=0)
    assert {entry.bucket for entry in entries} == {"2", "3+"}

def test_short_pools_return_what_exists():
    entries = select_experiment_tasks(pool(), {"near": 100, "far": 0, "none": 0}, 100, seed=0)
    assert len(entries) == 18

def test_write_manifest(tmp_path):
    entries = select_experiment_tasks(pool(), {"near": 2, "far": 0, "none": 0}, 5, seed=0)
    json_path, ids_path = tmp_path / "m.json", tmp_path / "ids.txt"
    write_manifest(entries, json_path, ids_path)
    assert len(ids_path.read_text().splitlines()) == 2
    assert json_path.read_text().startswith("[")