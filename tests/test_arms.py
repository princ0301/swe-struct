from pathlib import Path

import pytest
from pydantic import ValidationError

from swe_struct.agent.arms import ArmConfig, load_arms

CONFIG = Path(__file__).parent.parent / "configs" / "arms.yaml"

def test_all_six_arms_load():
    arms = load_arms(CONFIG)
    assert list(arms) == ["A1", "A2", "A3", "A4", "A5", "A6"]
    assert arms["A2"].id == "A2"

def test_arm_definitions_match_the_design():
    arms = load_arms(CONFIG)
    assert "graph_neighbors" not in arms["A1"].tools
    assert "graph_neighbors" in arms["A2"].tools
    assert arms["A3"].reminder
    assert arms["A4"].force_first_tool == "graph_neighbors"
    assert arms["A5"].passive_hints
    assert "graph_neighbors" not in arms["A5"].tools
    assert arms["A6"].shuffle_graph

def test_forced_tool_must_be_available():
    with pytest.raises(ValidationError):
        ArmConfig(id="X", name="x", tools=["submit"], force_first_tool="graph_neighbors")