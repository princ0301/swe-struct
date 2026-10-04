import shutil
import subprocess
from pathlib import Path

from conftest import FailingBackend, TINY_REPO
from swe_struct.agent.arms import load_arms
from swe_struct.agent.limits import Limits
from swe_struct.backends.mock import MockBackend, tool_reply
from swe_struct.core.schema import completed_run_ids, read_runs
from swe_struct.data.repos import RepoCache
from swe_struct.data.tasks import Task
from swe_struct.runner.matrix import run_task

ARMS = load_arms(Path(__file__).parent.parent / "configs" / "arms.yaml")

def git(cwd, *args):
    result = subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()

def make_origin(tmp_path):
    source = tmp_path / "origin" / "o" / "r"
    shutil.copytree(TINY_REPO, source)
    git(source, "init", "-b", "main")
    git(source, "add", ".")
    git(source, "commit", "-m", "one")
    commit = git(source, "rev-parse", "HEAD")
    cache = RepoCache(tmp_path / "cache", url_template=str(tmp_path / "origin") + "/{repo}")
    task = Task(
        instance_id="t-1",
        repo="o/r",
        base_commit=commit,
        problem_statement="`parse_config` is broken",
        patch="",
    )
    return cache, task

def submit_backend():
    return MockBackend([tool_reply("submit", {"files": ["app/config.py"]})])

def call(cache, task, output, done, factory=submit_backend, arm_ids=("A1", "A2", "A6"), seeds=(0, 1)):
    return run_task(
        task=task,
        arms=ARMS,
        arm_ids=list(arm_ids),
        model="m",
        backend_factory=factory,
        seeds=list(seeds),
        cache=cache,
        output=output,
        limits=Limits(max_steps=5),
        sampling={"temperature": 0.5},
        git_sha="sha",
        done=done,
        workers=2,
    )

def test_runs_every_arm_and_seed_then_resumes(tmp_path):
    cache, task = make_origin(tmp_path)
    output = tmp_path / "runs.jsonl"
    done: set[str] = set()
    summary = call(cache, task, output, done)
    assert (summary.executed, summary.skipped, summary.failed) == (6, 0, 0)
    assert len(read_runs(output)) == 6
    assert not (cache.cache_dir / "work" / "t-1").exists()
    again = call(cache, task, output, done)
    assert (again.executed, again.skipped) == (0, 6)
    fresh = call(cache, task, output, completed_run_ids(output))
    assert (fresh.executed, fresh.skipped) == (0, 6)

def test_unreachable_backend_writes_nothing_and_is_retried_later(tmp_path):
    cache, task = make_origin(tmp_path)
    output = tmp_path / "runs.jsonl"
    done: set[str] = set()
    summary = call(cache, task, output, done, factory=FailingBackend, arm_ids=("A1",), seeds=(0,))
    assert (summary.executed, summary.failed) == (0, 1)
    assert read_runs(output) == []
    retry = call(cache, task, output, done, arm_ids=("A1",), seeds=(0,))
    assert retry.executed == 1