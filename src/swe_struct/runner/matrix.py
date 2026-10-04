import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from swe_struct.agent.arms import ArmConfig
from swe_struct.agent.limits import Limits
from swe_struct.backends.backend import Backend
from swe_struct.core.ids import config_hash, run_id
from swe_struct.core.schema import append_run
from swe_struct.core.types import RepoContext
from swe_struct.data.repos import RepoCache
from swe_struct.data.tasks import Task
from swe_struct.graph.build import build_graph
from swe_struct.graph.shuffle import shuffle_edges
from swe_struct.runner.execute import execute_run, fingerprint

class TaskSummary(BaseModel):
    executed: int = 0
    skipped: int = 0
    failed: int = 0

def run_task(
    *,
    task: Task,
    arms: dict[str, ArmConfig],
    arm_ids: list[str],
    model: str,
    backend_factory: Callable[[], Backend],
    seeds: list[int],
    cache: RepoCache,
    output: Path,
    limits: Limits,
    sampling: dict[str, Any],
    git_sha: str,
    done: set[str],
    workers: int = 1,
    shuffle_seed: int = 0,
) -> TaskSummary:
    pending: list[tuple[ArmConfig, int]] = []
    for arm_id in arm_ids:
        arm = arms[arm_id]
        value = fingerprint(arm, limits, sampling)
        for seed in seeds:
            if run_id(model, arm_id, task.instance_id, seed, value) not in done:
                pending.append((arm, seed))
    total = len(arm_ids) * len(seeds)
    if not pending:
        return TaskSummary(skipped=total)
    workdir = cache.cache_dir / "work" / task.instance_id
    cache.checkout(task.repo, task.base_commit, workdir)
    try:
        graph = build_graph(workdir).graph
        shuffled = graph
        if any(arm.shuffle_graph for arm, _ in pending):
            task_seed = int(config_hash([shuffle_seed, task.instance_id])[:8], 16)
            shuffled = shuffle_edges(graph, task_seed)
        ctx = RepoContext(root=workdir)
        lock = threading.Lock()

        def work(item: tuple[ArmConfig, int]) -> bool:
            arm, seed = item
            record = execute_run(
                task=task,
                arm=arm,
                model=model,
                seed=seed,
                backend=backend_factory(),
                graph=shuffled if arm.shuffle_graph else graph,
                ctx=ctx,
                limits=limits,
                sampling=sampling,
                git_sha=git_sha,
            )
            if record is None:
                return False
            with lock:
                append_run(output, record)
                done.add(record.run_id)
            return True

        with ThreadPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(work, pending))
    finally:
        cache.remove(task.repo, workdir)
    executed = sum(results)
    return TaskSummary(executed=executed, skipped=total - len(pending), failed=len(results) - executed)