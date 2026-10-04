from pathlib import Path

import typer

from swe_struct.agent.arms import load_arms
from swe_struct.agent.limits import Limits
from swe_struct.backends.openai_compat import OpenAICompatBackend
from swe_struct.core.schema import completed_run_ids
from swe_struct.data.repos import RepoCache, current_git_sha
from swe_struct.data.tasks import DEFAULT_DATASET, load_swebench
from swe_struct.runner.matrix import run_task

def main(
    tasks_file: Path,
    arms: str = "A1,A2",
    seeds: str = "0",
    model: str = "gemma4:31b-cloud",
    base_url: str = "http://localhost:11434/v1",
    output: Path = Path("runs/logs/runs.jsonl"),
    cache_dir: Path = Path("data_cache"),
    arms_config: Path = Path("configs/arms.yaml"),
    workers: int = 1,
    max_steps: int = 30,
    temperature: float = 0.6,
    dataset: str = DEFAULT_DATASET,
) -> None:
    ids = [line.strip() for line in tasks_file.read_text().splitlines() if line.strip()]
    by_id = {task.instance_id: task for task in load_swebench(dataset)}
    arm_ids = [arm.strip() for arm in arms.split(",")]
    seed_list = [int(seed) for seed in seeds.split(",")]
    cache = RepoCache(cache_dir)
    done = completed_run_ids(output)
    git_sha = current_git_sha()
    for index, instance_id in enumerate(ids, start=1):
        summary = run_task(
            task=by_id[instance_id],
            arms=load_arms(arms_config),
            arm_ids=arm_ids,
            model=model,
            backend_factory=lambda: OpenAICompatBackend(base_url, model),
            seeds=seed_list,
            cache=cache,
            output=output,
            limits=Limits(max_steps=max_steps),
            sampling={"temperature": temperature},
            git_sha=git_sha,
            done=done,
            workers=workers,
        )
        typer.echo(f"{index}/{len(ids)} {instance_id} {summary.model_dump()}")

if __name__ == "__main__":
    typer.run(main)