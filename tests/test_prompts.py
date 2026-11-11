import json
import re
from pathlib import Path

import pytest

from atlas.prompts import PROMPTS, REASON_CODES, render

DATASET = Path(__file__).resolve().parents[1] / "data/samples/disputes_v1.jsonl"
FIELDS = {
    "case_id",
    "channel",
    "amount_usd",
    "merchant",
    "mcc",
    "cardholder_claim",
    "label_reason_code",
}
CASES = [json.loads(line) for line in DATASET.read_text().splitlines() if line.strip()]

CASE = {
    "case_id": "T-1",
    "channel": "online",
    "amount_usd": 10.0,
    "merchant": "Test Shop",
    "mcc": "5999",
    "cardholder_claim": "Never arrived.",
    "label_reason_code": "13.1",
}


@pytest.mark.parametrize("prompt_id", ["dispute_triage@v1", "dispute_triage@v2"])
def test_render_returns_system_and_user(prompt_id):
    messages = render(prompt_id, CASE)

    assert [m["role"] for m in messages] == ["system", "user"]
    assert "Never arrived." in messages[1]["content"]


def test_render_never_leaks_the_label():
    user_text = render("dispute_triage@v1", CASE)[1]["content"]

    assert "13.1" not in user_text


def test_unknown_prompt_id_raises():
    with pytest.raises(KeyError):
        render("dispute_triage@v99", CASE)


@pytest.mark.parametrize("prompt_id", list(PROMPTS))
def test_every_reason_code_is_in_every_prompt(prompt_id):
    for code in REASON_CODES:
        assert code in PROMPTS[prompt_id]


def test_dataset_shape():
    assert len(CASES) == 12
    assert len({c["case_id"] for c in CASES}) == len(CASES)
    for case in CASES:
        assert set(case) == FIELDS, case["case_id"]


def test_dataset_labels_are_valid_and_cover_every_code():
    labels = {c["label_reason_code"] for c in CASES}

    assert labels <= set(REASON_CODES)
    assert labels == set(REASON_CODES)


def test_dataset_has_no_card_numbers():
    # A PAN is 12 to 19 digits; no field in synthetic data needs a run that long.
    assert not re.search(r"\d{12,}", DATASET.read_text())


@pytest.mark.parametrize("prompt_id", list(PROMPTS))
@pytest.mark.parametrize("case", CASES, ids=lambda c: c["case_id"])
def test_every_prompt_renders_every_case(prompt_id, case):
    system, user = render(prompt_id, case)

    assert system["content"] == PROMPTS[prompt_id]
    assert case["cardholder_claim"] in user["content"]
    assert case["label_reason_code"] not in user["content"]
