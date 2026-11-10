import pandas as pd
import pytest

from atlas import scorecard
from atlas.scorecard import load_cases, predicted_code, run_experiment, summarize


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
    # Autouse fixture sets ATLAS_MOCK=1: real call_model, no network, a valid JSON reply.
    variants = [{"prompt_id": "dispute_triage@v2", "model": "openai/atlas-ci-mock", "params": {}}]

    df = run_experiment(variants, [make_case("C-1", "13.1")])

    assert df.loc[0, "error"] is None
    assert df.loc[0, "valid_json"]
    assert df.loc[0, "correct"]  # the mock always answers 13.1


def test_predicted_code_needs_a_reason_code():
    assert predicted_code('Answer: {"reason_code": " 13.1 "}') == "13.1"
    assert predicted_code('{"confidence": 0.5}') is None
    assert predicted_code("mock reply") is None


def test_load_cases_skips_blank_lines(tmp_path):
    path = tmp_path / "cases.jsonl"
    path.write_text('{"case_id": "A"}\n\n{"case_id": "B"}\n')

    assert [c["case_id"] for c in load_cases(path)] == ["A", "B"]


def test_summarize_has_one_row_per_variant_and_counts_failures(monkeypatch):
    def fake_call(model, messages, **params):
        if model == "broken":
            return fake_result("", error="RateLimitError: 429")
        return fake_result('{"reason_code": "13.1"}')

    monkeypatch.setattr(scorecard, "call_model", fake_call)
    variants = [
        {"name": "ok", "prompt_id": "dispute_triage@v1", "model": "fake", "params": {}},
        {"name": "down", "prompt_id": "dispute_triage@v1", "model": "broken", "params": {}},
    ]

    summary = summarize(run_experiment(variants, [make_case("C-1", "13.1")] * 3))

    assert list(summary.index) == ["ok", "down"]
    assert {
        "accuracy",
        "valid_json_rate",
        "error_rate",
        "p50_latency_ms",
        "p95_latency_ms",
        "avg_reasoning_tokens",
        "cost_per_1k_usd",
    } <= set(summary.columns)
    assert summary.loc["ok", "accuracy"] == 1.0
    assert summary.loc["down", "error_rate"] == 1.0
    assert summary.loc["down", "accuracy"] == 0.0


def test_duplicate_variant_names_are_rejected():
    variant = {"name": "same", "prompt_id": "dispute_triage@v1", "model": "fake", "params": {}}

    with pytest.raises(ValueError, match="same"):
        run_experiment([variant, dict(variant)], [make_case("C-1", "13.1")])


def test_optional_delay_between_calls(monkeypatch):
    sleeps = []
    monkeypatch.setenv("ATLAS_CALL_DELAY_S", "0.5")
    monkeypatch.setattr(scorecard.time, "sleep", sleeps.append)
    monkeypatch.setattr(scorecard, "call_model", lambda m, msgs, **p: fake_result("{}"))
    variant = {"name": "v", "prompt_id": "dispute_triage@v1", "model": "fake", "params": {}}

    run_experiment([variant], [make_case(f"C-{i}", "13.1") for i in range(3)])

    assert sleeps == [0.5, 0.5]  # between calls, not before the first


def test_cost_per_success_ignores_failed_calls(monkeypatch):
    replies = iter(
        [
            fake_result('{"reason_code": "13.1"}'),  # costs 0.001
            fake_result("", error="Timeout: slow") | {"cost_usd": 0.0},
        ]
    )
    monkeypatch.setattr(scorecard, "call_model", lambda m, msgs, **p: next(replies))
    variant = {"name": "flaky", "prompt_id": "dispute_triage@v1", "model": "fake", "params": {}}

    row = summarize(run_experiment([variant], [make_case("C-1", "13.1")] * 2)).loc["flaky"]

    assert row["n_success"] == 1
    assert row["cost_per_1k_usd"] == pytest.approx(0.5)  # the failure drags the mean down
    assert row["cost_per_1k_success_usd"] == pytest.approx(1.0)  # the real price of an answer


def test_cost_per_success_is_nan_when_every_call_fails(monkeypatch):
    monkeypatch.setattr(
        scorecard, "call_model", lambda m, msgs, **p: fake_result("", error="RateLimitError: 429")
    )
    variant = {"name": "down", "prompt_id": "dispute_triage@v1", "model": "fake", "params": {}}

    row = summarize(run_experiment([variant], [make_case("C-1", "13.1")])).loc["down"]

    assert row["n_success"] == 0
    assert pd.isna(row["cost_per_1k_success_usd"])
