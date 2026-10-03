import hashlib
import json
from typing import Any

def config_hash(config: Any) -> str:
    canonical = json.dumps(config, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:12]

def run_id(model: str, arm: str, task_id: str, seed: int, cfg_hash: str) -> str:
    return config_hash(
        {"model": model, "arm": arm, "task": task_id, "seed": seed, "config": cfg_hash}
    )