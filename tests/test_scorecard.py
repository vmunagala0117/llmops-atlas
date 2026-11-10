import pytest

from atlas import scorecard
from atlas.scorecard import parse_response, run_experiment, summarize


def make_case(case_id, label):
    return {
        "case_id": case_id,
        "channel": "online",
        "amount_usd": 10.0,
        "merchant": "Test Shop",
        "mcc": "5999",
        "cardholder_claim": "claim",
        "label_reason_code": label,
    }


@pytest.mark.parametrize(
    "text",
    [
        '{"reason_code": "13.1", "confidence": 0.8}',
        '```json\n{"reason_code": "13.1"}\n```',
        'Here you go: {"reason_code": " 13.1 "} thanks',
    ],
)
def test_parse_accepts_json_with_noise(text):
    assert parse_response(text)["reason_code"] == "13.1"


@pytest.mark.parametrize(
    "text", [None, "", "mock reply", "{not json}", '{"confidence": 0.5}', "[1, 2]"]
)
def test_parse_rejects_unusable_replies(text):
    assert parse_response(text) is None


def fake_result(text, error=None, latency_ms=100):
    return {
        "model": "fake",
        "text": text,
        "prompt_tokens": 50,
        "completion_tokens": 20,
        "reasoning_tokens": 10,
        "cost_usd": 0.001,
        "latency_ms": latency_ms,
        "error": error,
    }


def test_run_experiment_and_summarize(monkeypatch):
    replies = iter(
        [
            fake_result('{"reason_code": "13.1"}', latency_ms=100),  # correct
            fake_result('{"reason_code": "13.7"}', latency_ms=200),  # wrong
            fake_result("not json", latency_ms=300),  # invalid
            fake_result("", error="Timeout: slow", latency_ms=400),  # provider error
        ]
    )
    monkeypatch.setattr(scorecard, "call_model", lambda model, messages, **p: next(replies))
    cases = [make_case(f"C-{i}", "13.1") for i in range(4)]
    variants = [{"prompt_id": "dispute_triage@v1", "model": "fake", "params": {}}]

    df = run_experiment(variants, cases)
    row = summarize(df).loc["dispute_triage@v1 effort=default"]

    assert list(df["correct"]) == [True, False, False, False]
    assert row["n"] == 4
    assert row["accuracy"] == 0.25
    assert row["valid_json_rate"] == 0.5
    assert row["error_rate"] == 0.25
    assert row["p50_latency_ms"] == 250
    assert row["avg_reasoning_tokens"] == 10
    assert row["cost_per_1k_usd"] == pytest.approx(1.0)


def test_variant_name_uses_reasoning_effort():
    variant = {"prompt_id": "dispute_triage@v2", "params": {"reasoning_effort": "minimal"}}

    assert scorecard.variant_name(variant) == "dispute_triage@v2 effort=minimal"


def test_mock_mode_runs_end_to_end():
    # Autouse fixture sets ATLAS_MOCK=1: real call_model, no network, replies are not JSON.
    variants = [{"prompt_id": "dispute_triage@v2", "model": "openai/atlas-ci-mock", "params": {}}]

    df = run_experiment(variants, [make_case("C-1", "13.1")])

    assert df.loc[0, "error"] is None
    assert not df.loc[0, "valid_json"]
