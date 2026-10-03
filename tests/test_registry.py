import pytest

from swe_struct.tools.registry import ToolRegistry
from swe_struct.tools.submit import SubmitTool

def test_unknown_tool_is_reported(registry, ctx):
    result = registry.call("nope", ctx, {})
    assert not result.ok
    assert "unknown tool" in result.content

def test_bad_arguments_are_reported(registry, ctx):
    result = registry.call("echo", ctx, {"wrong": 1})
    assert not result.ok
    assert "invalid arguments" in result.content

def test_call_returns_tool_output(registry, ctx):
    assert registry.call("echo", ctx, {"text": "hi"}).content == "hi"

def test_specs_follow_requested_names(registry):
    assert [spec.name for spec in registry.specs(["submit", "echo"])] == ["submit", "echo"]

def test_duplicate_registration_fails():
    registry = ToolRegistry([SubmitTool()])
    with pytest.raises(ValueError):
        registry.register(SubmitTool())