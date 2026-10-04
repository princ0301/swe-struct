import json

import httpx

from swe_struct.backends.openai_compat import OpenAICompatBackend, message_to_wire
from swe_struct.core.types import Message, ToolCall, ToolSpec

def make_backend(handler) -> OpenAICompatBackend:
    client = httpx.Client(base_url="http://test/v1/", transport=httpx.MockTransport(handler))
    return OpenAICompatBackend(base_url="http://test/v1", model="m", client=client)

def tool_payload(arguments: str) -> dict:
    return {
        "choices": [
            {
                "message": {
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "c1",
                            "type": "function",
                            "function": {"name": "echo", "arguments": arguments},
                        }
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ],
        "usage": {"prompt_tokens": 12, "completion_tokens": 3},
    }

def test_request_and_tool_call_parsing():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=tool_payload('{"text": "hi"}'))

    spec = ToolSpec(name="echo", description="d", parameters={"type": "object"})
    result = make_backend(handler).chat(
        [Message(role="user", content="go")], [spec], temperature=0.0
    )
    assert seen["path"] == "/v1/chat/completions"
    assert seen["body"]["model"] == "m"
    assert seen["body"]["temperature"] == 0.0
    assert seen["body"]["tools"][0]["function"]["name"] == "echo"
    assert result.tool_calls[0].arguments == {"text": "hi"}
    assert result.usage.prompt_tokens == 12
    assert result.finish_reason == "tool_calls"
    assert result.latency_s >= 0

def test_malformed_arguments_are_kept_raw():
    backend = make_backend(lambda request: httpx.Response(200, json=tool_payload("{bad")))
    result = backend.chat([Message(role="user", content="go")], [])
    assert result.tool_calls[0].arguments == {"_raw": "{bad"}

def test_plain_text_reply():
    payload = {"choices": [{"message": {"content": "hello"}, "finish_reason": "stop"}]}
    backend = make_backend(lambda request: httpx.Response(200, json=payload))
    result = backend.chat([Message(role="user", content="go")], [])
    assert result.content == "hello"
    assert result.tool_calls == []

def test_assistant_tool_call_wire_format():
    message = Message(
        role="assistant",
        tool_calls=[ToolCall(id="c1", name="echo", arguments={"text": "hi"})],
    )
    wire = message_to_wire(message)
    assert wire["content"] == ""
    assert json.loads(wire["tool_calls"][0]["function"]["arguments"]) == {"text": "hi"}

def test_explicit_tool_choice_is_forwarded():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=tool_payload("{}"))

    spec = ToolSpec(name="echo", description="d", parameters={"type": "object"})
    forced = {"type": "function", "function": {"name": "echo"}}
    make_backend(handler).chat([Message(role="user", content="go")], [spec], tool_choice=forced)
    assert seen["body"]["tool_choice"] == forced

def test_default_tool_choice_is_auto():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=tool_payload("{}"))

    spec = ToolSpec(name="echo", description="d", parameters={"type": "object"})
    make_backend(handler).chat([Message(role="user", content="go")], [spec])
    assert seen["body"]["tool_choice"] == "auto"