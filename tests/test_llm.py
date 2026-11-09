from types import SimpleNamespace

from atlas import llm

EXPECTED_KEYS = {
    "model",
    "text",
    "prompt_tokens",
    "completion_tokens",
    "reasoning_tokens",
    "cost_usd",
    "latency_ms",
    "error",
}
MESSAGES = [{"role": "user", "content": "Reply with one word: ready"}]


def test_mock_mode_returns_all_fields():
    result = llm.call_model("gpt-5-mini", MESSAGES)

    assert set(result) == EXPECTED_KEYS
    assert result["error"] is None
    assert result["text"] == llm.MOCK_REPLY


def test_mock_mode_cost_is_zero():
    result = llm.call_model("gpt-5-mini", MESSAGES)

    assert result["cost_usd"] == 0.0


def test_missing_reasoning_tokens_gives_zero(monkeypatch):
    def fake_completion(**kwargs):
        usage = SimpleNamespace(prompt_tokens=12, completion_tokens=3)  # no details field
        message = SimpleNamespace(content="ready")
        return SimpleNamespace(choices=[SimpleNamespace(message=message)], usage=usage)

    monkeypatch.setattr(llm.litellm, "completion", fake_completion)

    result = llm.call_model("gpt-5-mini", MESSAGES)

    assert result["error"] is None
    assert result["reasoning_tokens"] == 0
    assert result["completion_tokens"] == 3
    assert result["cost_usd"] == 0.0


def test_provider_error_becomes_error_value(monkeypatch):
    def fake_completion(**kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(llm.litellm, "completion", fake_completion)

    result = llm.call_model("gpt-5-mini", MESSAGES)

    assert set(result) == EXPECTED_KEYS
    assert result["error"] == "RuntimeError: boom"
    assert result["text"] == ""
