from swe_struct.agent.limits import Limits
from swe_struct.agent.loop import TRUNCATION_MARKER, run_agent
from swe_struct.backends.mock import MockBackend, text_reply, tool_reply
from swe_struct.core.types import Message

NAMES = ["echo", "submit"]

def run(backend, registry, ctx, limits=None):
    return run_agent(
        backend=backend,
        registry=registry,
        ctx=ctx,
        messages=[Message(role="user", content="task")],
        tool_names=NAMES,
        limits=limits or Limits(max_steps=5),
    )

def test_submit_ends_the_run(registry, ctx):
    backend = MockBackend(
        [
            tool_reply("echo", {"text": "hi"}),
            tool_reply("submit", {"files": ["a.py"], "functions": ["a.f"]}),
        ]
    )
    outcome = run(backend, registry, ctx)
    assert outcome.stop_reason == "submitted"
    assert len(outcome.steps) == 2
    assert outcome.submission == {"files": ["a.py"], "functions": ["a.f"]}
    assert outcome.steps[0].tool_events[0].name == "echo"
    assert backend.calls[1][-1].role == "tool"
    assert backend.calls[1][-1].content == "hi"

def test_reply_without_tool_call_stops(registry, ctx):
    outcome = run(MockBackend([text_reply("done")]), registry, ctx)
    assert outcome.stop_reason == "no_tool_call"
    assert outcome.submission is None

def test_step_limit(registry, ctx):
    script = [tool_reply("echo", {"text": "x"}) for _ in range(5)]
    outcome = run(MockBackend(script), registry, ctx, Limits(max_steps=2))
    assert outcome.stop_reason == "max_steps"
    assert len(outcome.steps) == 2

def test_long_output_is_truncated(registry, ctx):
    backend = MockBackend([tool_reply("echo", {"text": "x" * 50}), text_reply("done")])
    outcome = run(backend, registry, ctx, Limits(max_steps=5, max_tool_output_chars=10))
    event = outcome.steps[0].tool_events[0]
    assert event.truncated
    assert event.result_chars == 50
    assert backend.calls[1][-1].content == "x" * 10 + TRUNCATION_MARKER

def test_unknown_tool_is_logged_as_failed(registry, ctx):
    backend = MockBackend([tool_reply("nope", {}), text_reply("done")])
    outcome = run(backend, registry, ctx)
    assert not outcome.steps[0].tool_events[0].ok