import json
import math
from types import SimpleNamespace

import pytest

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
    assert result["cost_usd"] == 0.0  # mock mode never prices tokens


def test_provider_error_becomes_error_value(monkeypatch):
    def fake_completion(**kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(llm.litellm, "completion", fake_completion)

    result = llm.call_model("gpt-5-mini", MESSAGES)

    assert set(result) == EXPECTED_KEYS
    assert result["error"] == "RuntimeError: boom"
    assert result["text"] == ""


def test_mock_reply_follows_the_output_contract():
    answer = json.loads(llm.MOCK_REPLY)

    assert set(answer) == {"reason_code", "confidence", "summary", "missing_evidence"}


def _fake_completion(**kwargs):
    usage = SimpleNamespace(prompt_tokens=12, completion_tokens=3)
    message = SimpleNamespace(content="ready")
    return SimpleNamespace(choices=[SimpleNamespace(message=message)], usage=usage)


def test_known_price_is_reported(monkeypatch):
    monkeypatch.delenv("ATLAS_MOCK")  # pricing only runs outside mock; completion is faked
    monkeypatch.setattr(llm.litellm, "completion", _fake_completion)
    monkeypatch.setattr(llm.litellm, "completion_cost", lambda **kwargs: 0.002)

    assert llm.call_model("gpt-5-mini", MESSAGES)["cost_usd"] == 0.002


def test_unknown_price_is_nan_not_zero(monkeypatch):
    def no_price(**kwargs):
        raise ValueError("model not in the price map")

    monkeypatch.delenv("ATLAS_MOCK")
    monkeypatch.setattr(llm.litellm, "completion", _fake_completion)
    monkeypatch.setattr(llm.litellm, "completion_cost", no_price)

    result = llm.call_model("atlas-unpriced-deployment", MESSAGES)

    assert result["error"] is None
    assert math.isnan(result["cost_usd"])


def test_mock_embeddings_are_deterministic_and_1536_long(monkeypatch):
    def no_network(**kwargs):
        raise AssertionError("mock embed must not call LiteLLM")

    monkeypatch.setattr(llm.litellm, "embedding", no_network)

    first = llm.embed(["refund confirmed in writing", "item never arrived"])
    again = llm.embed(["refund confirmed in writing", "item never arrived"])

    assert first == again
    assert all(len(v) == llm.EMBED_DIM == 1536 for v in first)
    assert first[0] != first[1]
    assert math.isclose(sum(x * x for x in first[0]), 1.0)


def test_mock_embed_model_is_labelled_as_mock():
    assert llm.embed_model_name() == llm.MOCK_EMBED_MODEL


def _fake_embedding(dim):
    def fake(**kwargs):
        # Returned out of order on purpose: embed() must sort by index.
        items = [{"index": i, "embedding": [float(i)] * dim} for i in range(len(kwargs["input"]))]
        return SimpleNamespace(data=list(reversed(items)))

    return fake


def test_live_embed_keeps_input_order(monkeypatch):
    monkeypatch.delenv("ATLAS_MOCK")
    monkeypatch.setenv("ATLAS_EMBED_MODEL", "openai/atlas-test-embed")
    monkeypatch.setattr(llm.litellm, "embedding", _fake_embedding(llm.EMBED_DIM))

    vectors = llm.embed(["a", "b", "c"])

    assert [v[0] for v in vectors] == [0.0, 1.0, 2.0]


def test_live_embed_rejects_wrong_dimensions(monkeypatch):
    monkeypatch.delenv("ATLAS_MOCK")
    monkeypatch.setenv("ATLAS_EMBED_MODEL", "openai/atlas-test-embed")
    monkeypatch.setattr(llm.litellm, "embedding", _fake_embedding(3072))

    with pytest.raises(RuntimeError, match="3072 dimensions"):
        llm.embed(["a"])


def test_live_embed_needs_a_model_name(monkeypatch):
    monkeypatch.delenv("ATLAS_MOCK")
    monkeypatch.delenv("ATLAS_EMBED_MODEL", raising=False)

    with pytest.raises(RuntimeError, match="ATLAS_EMBED_MODEL"):
        llm.embed(["a"])


def test_cosine():
    assert math.isclose(llm.cosine([1.0, 0.0], [2.0, 0.0]), 1.0)
    assert math.isclose(llm.cosine([1.0, 0.0], [0.0, 3.0]), 0.0)
    assert math.isclose(llm.cosine([1.0, 1.0], [-1.0, -1.0]), -1.0)
