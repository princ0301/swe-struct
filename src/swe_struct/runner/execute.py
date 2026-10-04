from typing import Any

import httpx

from swe_struct.agent.arms import ArmConfig
from swe_struct.agent.limits import Limits
from swe_struct.agent.loop import run_agent
from swe_struct.agent.prompts import (
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    build_user_prompt,
    render_hints,
)
from swe_struct.backends.backend import Backend
from swe_struct.core.ids import config_hash, run_id
from swe_struct.core.schema import RunRecord
from swe_struct.core.types import Message, RepoContext
from swe_struct.data.anchors import find_anchors
from swe_struct.data.tasks import Task
from swe_struct.graph.model import CodeGraph
from swe_struct.tools.graph_neighbors import DEFAULT_DESCRIPTION, GraphNeighborsTool
from swe_struct.tools.list_dir import ListDirTool
from swe_struct.tools.registry import ToolRegistry
from swe_struct.tools.search_text import SearchTextTool
from swe_struct.tools.submit import SubmitTool
from swe_struct.tools.view_file import ViewFileTool

def build_registry(graph: CodeGraph, arm: ArmConfig) -> ToolRegistry:
    description = arm.graph_tool_description or DEFAULT_DESCRIPTION
    return ToolRegistry(
        [
            ListDirTool(),
            ViewFileTool(),
            SearchTextTool(),
            GraphNeighborsTool(graph, description),
            SubmitTool(),
        ]
    )

def fingerprint(arm: ArmConfig, limits: Limits, sampling: dict[str, Any]) -> str:
    return config_hash(
        {
            "arm": arm.model_dump(),
            "limits": limits.model_dump(),
            "sampling": sampling,
            "prompt_version": PROMPT_VERSION,
            "system_prompt": SYSTEM_PROMPT,
        }
    )

def execute_run(
    *,
    task: Task,
    arm: ArmConfig,
    model: str,
    seed: int,
    backend: Backend,
    graph: CodeGraph,
    ctx: RepoContext,
    limits: Limits,
    sampling: dict[str, Any],
    git_sha: str,
) -> RunRecord | None:
    hints = None
    if arm.passive_hints:
        hints = render_hints(graph, find_anchors(task.problem_statement, graph).anchors)
    messages = [
        Message(role="system", content=SYSTEM_PROMPT),
        Message(role="user", content=build_user_prompt(task.problem_statement, arm, hints)),
    ]
    try:
        outcome = run_agent(
            backend=backend,
            registry=build_registry(graph, arm),
            ctx=ctx,
            messages=messages,
            tool_names=arm.tools,
            limits=limits,
            sampling={**sampling, "seed": seed},
            forced_first_tool=arm.force_first_tool,
        )
    except httpx.HTTPError:
        return None
    fingerprint_value = fingerprint(arm, limits, sampling)
    return RunRecord(
        run_id=run_id(model, arm.id, task.instance_id, seed, fingerprint_value),
        task_id=task.instance_id,
        arm=arm.id,
        model=model,
        seed=seed,
        git_sha=git_sha,
        config_hash=fingerprint_value,
        stop_reason=outcome.stop_reason,
        steps=outcome.steps,
        submission=outcome.submission,
    )