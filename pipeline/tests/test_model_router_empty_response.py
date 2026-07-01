from types import SimpleNamespace

import pytest

from agent.model_router import _extract_chat_response


def _fake_response(*, content=None, tool_calls=None, error=None):
    message = SimpleNamespace(content=content, tool_calls=tool_calls)
    choice = SimpleNamespace(message=message, error=error)
    return SimpleNamespace(choices=[choice], usage=None)


def test_raises_when_no_content_and_no_tool_calls():
    # Reasoning-only models (e.g. Gemini 2.5 Flash Lite via OpenRouter) can stop
    # after spending the whole completion on hidden reasoning tokens, returning
    # neither visible content nor a tool call. That must fail over, not surface
    # as a silent "" reply to the user.
    with pytest.raises(ValueError, match="empty content"):
        _extract_chat_response(_fake_response(content=None, tool_calls=None))


def test_raises_on_embedded_choice_error():
    with pytest.raises(ValueError, match="embedded error"):
        _extract_chat_response(_fake_response(error={"code": 429, "message": "rate_limit_exceeded"}))


def test_passes_through_with_content():
    msg_dict, _usage = _extract_chat_response(_fake_response(content="hello"))
    assert msg_dict["content"] == "hello"


def test_passes_through_with_tool_calls_only():
    tc = SimpleNamespace(id="1", type="function", function=SimpleNamespace(name="foo", arguments="{}"))
    msg_dict, _usage = _extract_chat_response(_fake_response(content=None, tool_calls=[tc]))
    assert msg_dict["tool_calls"][0]["function"]["name"] == "foo"
