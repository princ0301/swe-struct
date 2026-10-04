from pathlib import Path

from swe_struct.agent.arms import load_arms
from swe_struct.agent.limits import Limits
from swe_struct.backends.mock import MockBackend, text_reply, tool_reply
from swe_struct.data.tasks import Task
from swe_struct.graph.build import build_graph
from swe_struct.runner.execute import execute_run

ARMS = load_arms(Path(__file__).parent.parent / "configs" / "arms.yaml")
SUBMIT = tool_reply("submit", {"files": ["app/config.py"], "functions": ["app/config.py::parse_config"]})
TASK = Task(
    instance_id="t-1",
    repo="o/r",
    base_commit="abc",
    problem_statement="`parse_config` is broken",
    patch="",
)

def run(repo, arm_id, script, seed=0, backend=None):
    backend = backend or MockBackend(script)
    record = execute_run(
        task=TASK,
        arm=ARMS[arm_id],
        model="m",
        seed=seed,
        backend=backend,
        graph=build_graph(repo.root).graph,
        ctx=repo,
        limits=Limits(max_steps=5),
        sampling={"temperature": 0.5},
        git_sha="sha",
    )
    return record, backend

def test_optional_graph_tool_run(repo):
    script = [tool_reply("graph_neighbors", {"symbol": "parse_config"}), SUBMIT]
    record, _ = run(repo, "A2", script)
    assert record.arm == "A2"
    assert record.stop_reason == "submitted"
    assert record.steps[0].tool_events[0].name == "graph_neighbors"
    assert record.steps[0].tool_events[0].ok
    assert record.submission["functions"] == ["app/config.py::parse_config"]
    assert record.git_sha == "sha"

def test_graph_tool_is_unavailable_in_the_baseline_arm(repo):
    record, _ = run(repo, "A1", [tool_reply("graph_neighbors", {"symbol": "parse_config"}), SUBMIT])
    assert not record.steps[0].tool_events[0].ok

def test_forced_arm_forces_only_the_first_turn_and_passes_the_seed(repo):
    script = [tool_reply("graph_neighbors", {"symbol": "parse_config"}), SUBMIT]
    _, backend = run(repo, "A4", script, seed=3)
    forced = {"type": "function", "function": {"name": "graph_neighbors"}}
    assert backend.sampling_calls[0]["tool_choice"] == forced
    assert "tool_choice" not in backend.sampling_calls[1]
    assert backend.sampling_calls[0]["seed"] == 3
    assert backend.sampling_calls[0]["temperature"] == 0.5

def test_reminder_reaches_the_prompt(repo):
    _, backend = run(repo, "A3", [SUBMIT])
    assert "graph_neighbors" in backend.calls[0][1].content
    _, other = run(repo, "A2", [SUBMIT])
    assert "Before you submit" not in other.calls[0][1].content

def test_passive_hints_reach_the_prompt(repo):
    _, backend = run(repo, "A5", [SUBMIT])
    assert "hop 1 caller: app/config.py::load_config" in backend.calls[0][1].content

def test_run_ids_are_stable_and_distinguish_arms_and_seeds(repo):
    first, _ = run(repo, "A2", [SUBMIT])
    again, _ = run(repo, "A2", [SUBMIT])
    other_arm, _ = run(repo, "A3", [SUBMIT])
    other_seed, _ = run(repo, "A2", [SUBMIT], seed=1)
    assert first.run_id == again.run_id
    assert len({first.run_id, other_arm.run_id, other_seed.run_id}) == 3
    assert first.config_hash == other_seed.config_hash

def test_unreachable_backend_returns_none(repo, registry):
    from conftest import FailingBackend

    record, _ = run(repo, "A2", [], backend=FailingBackend())
    assert record is None