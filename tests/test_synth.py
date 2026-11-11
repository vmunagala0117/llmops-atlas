import json
import re
from collections import Counter
from pathlib import Path

import pytest

from atlas.prompts import REASON_CODES
from atlas.synth import TEMPLATES, generate_disputes

DATA = Path(__file__).resolve().parents[1] / "data" / "synthetic"
FIELDS = {
    "case_id",
    "split",
    "channel",
    "amount_usd",
    "merchant",
    "mcc",
    "transaction_date",
    "cardholder_claim",
    "label_reason_code",
    "difficulty",
    "template_id",
    "alt_reason_code",  # extra field, see Decisions in spec 2.1
}
CASES = generate_disputes(200, 42)


def by_split(cases, split):
    return [c for c in cases if c["split"] == split]


def test_same_seed_same_output():
    assert generate_disputes(200, 42) == CASES
    assert generate_disputes(200, 7) != CASES


def test_committed_files_match_the_generator():
    # Fails if templates or the Faker version change without rerunning make_dataset.py.
    def read(name):
        return [json.loads(line) for line in (DATA / name).read_text().splitlines()]

    assert read("disputes_dev.jsonl") == by_split(CASES, "dev")
    assert read("disputes_heldout.jsonl") == by_split(CASES, "held_out")


def test_fields_and_values():
    assert len({c["case_id"] for c in CASES}) == len(CASES) == 200
    for case in CASES:
        assert set(case) == FIELDS
        assert case["label_reason_code"] in REASON_CODES
        assert case["split"] in {"dev", "held_out"}
        assert case["difficulty"] in {"standard", "ambiguous"}


def test_alt_code_only_on_ambiguous_cases():
    for case in CASES:
        if case["difficulty"] == "standard":
            assert case["alt_reason_code"] is None
        else:
            assert case["alt_reason_code"] in REASON_CODES
            assert case["alt_reason_code"] != case["label_reason_code"]


@pytest.mark.parametrize("split", ["dev", "held_out"])
def test_every_split_has_every_code_and_ambiguous_cases(split):
    cases = by_split(CASES, split)

    assert {c["label_reason_code"] for c in cases} == set(REASON_CODES)
    assert any(c["difficulty"] == "ambiguous" for c in cases)


def test_split_is_about_25_percent_per_code():
    per_code = Counter(c["label_reason_code"] for c in CASES)
    held = Counter(c["label_reason_code"] for c in by_split(CASES, "held_out"))

    for code in REASON_CODES:
        assert 0.2 <= held[code] / per_code[code] <= 0.3


def test_codes_are_balanced():
    counts = Counter(c["label_reason_code"] for c in CASES)

    assert max(counts.values()) - min(counts.values()) <= 1


@pytest.mark.parametrize("seed", [42, 1, 2024])
def test_ambiguous_share_between_10_and_20_percent(seed):
    cases = generate_disputes(200, seed)
    share = sum(c["difficulty"] == "ambiguous" for c in cases) / len(cases)

    assert 0.10 <= share <= 0.20


def test_no_template_is_shared_between_splits():
    dev = {c["template_id"] for c in by_split(CASES, "dev")}
    held = {c["template_id"] for c in by_split(CASES, "held_out")}

    assert not dev & held


def test_at_least_3_templates_per_code():
    per_code = Counter(t.label for t in TEMPLATES)

    assert all(per_code[code] >= 3 for code in REASON_CODES)


def test_every_template_is_used():
    assert {t.template_id for t in TEMPLATES} == {c["template_id"] for c in CASES}


def test_no_card_numbers_and_card_absent_fraud():
    for case in CASES:
        assert not re.search(r"\d{12,}", json.dumps(case))
        if case["label_reason_code"] == "10.4":
            assert case["channel"] != "in_store"  # 10.4 is card-absent fraud


def test_claim_agrees_with_the_fields():
    # Typos never touch digits or the merchant name, so these always survive.
    text_of = {t.template_id: t.text for t in TEMPLATES}
    for case in CASES:
        claim = case["cardholder_claim"]
        assert case["merchant"] in claim
        if "{amount}" in text_of[case["template_id"]]:
            assert f"{case['amount_usd']:.2f}" in claim


def test_too_small_n_raises():
    with pytest.raises(ValueError, match="too small"):
        generate_disputes(16, 42)
