from pathlib import Path

from swe_struct.agent.arms import load_arms
from swe_struct.agent.prompts import (
    MAX_BLOCK_LINES,
    MAX_ISSUE_CHARS,
    REMINDER,
    build_user_prompt,
    render_hints,
)
from swe_struct.graph.build import build_graph

ARMS = load_arms(Path(__file__).parent.parent / "configs" / "arms.yaml")

def test_issue_is_truncated():
    prompt = build_user_prompt("Q" * (MAX_ISSUE_CHARS + 50), ARMS["A1"], None)
    assert prompt.count("Q") == MAX_ISSUE_CHARS

def test_reminder_only_for_reminder_arm():
    assert REMINDER in build_user_prompt("issue", ARMS["A3"], None)
    assert REMINDER not in build_user_prompt("issue", ARMS["A2"], None)

def test_hints_are_included_when_given():
    prompt = build_user_prompt("issue", ARMS["A5"], "hop 1 caller: x")
    assert "Repository structure hints:\nhop 1 caller: x" in prompt
    assert "Repository structure hints" not in build_user_prompt("issue", ARMS["A5"], None)

def test_hints_list_neighbors_of_anchors(repo):
    graph = build_graph(repo.root).graph
    hints = render_hints(graph, ["app/config.py::load_config"])
    assert hints is not None
    assert "hop 1 caller: app/main.py::Runner.run" in hints
    assert "hop 1 callee: app/config.py::parse_config" in hints

def test_no_hints_without_connected_anchors(repo):
    graph = build_graph(repo.root).graph
    assert render_hints(graph, []) is None
    assert render_hints(graph, ["app/__init__.py"]) is None

def test_hint_blocks_are_capped(tmp_path):
    body = "".join(f"def f{i}():\n    pass\n\n" for i in range(60))
    (tmp_path / "big.py").write_text(body)
    graph = build_graph(tmp_path).graph
    hints = render_hints(graph, ["big.py"])
    assert hints is not None
    assert len(hints.splitlines()) == MAX_BLOCK_LINES