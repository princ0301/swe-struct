import pytest

from swe_struct.backends.mock import MockBackend, text_reply, tool_reply
from swe_struct.core.types import Message

def test_script_is_returned_in_order():
    backend = MockBackend([tool_reply("echo", {"text": "a"}), text_reply("done")])
    messages = [Message(role="user", content="go")]
    assert backend.chat(messages, []).tool_calls[0].name == "echo"
    assert backend.chat(messages, []).content == "done"
    assert len(backend.calls) == 2

def test_exhausted_script_raises():
    backend = MockBackend([])
    with pytest.raises(RuntimeError):
        backend.chat([], [])