import json
import subprocess
import sys
from pathlib import Path

import pytest

from atlas.pii import find_pii, load_allowlist, luhn_valid
from atlas.synth import generate_disputes

ROOT = Path(__file__).resolve().parents[1]
SCAN = ROOT / "scripts" / "scan_data.py"
ALLOWLIST = load_allowlist(ROOT / "config" / "pii_allowlist.txt")
VISA_TEST = "4111111111111111"  # published test number, listed in the allowlist


def types(text):
    return [f["type"] for f in find_pii(text)]


def with_check_digit(body):
    # Builds a Luhn-valid number at runtime, so no unlisted literal sits in this file.
    return next(body + d for d in "0123456789" if luhn_valid(body + d))


def run_scan(*paths):
    return subprocess.run(
        [sys.executable, str(SCAN), *map(str, paths)], capture_output=True, text=True
    )


def test_luhn_valid_and_invalid():
    assert luhn_valid(VISA_TEST)
    assert luhn_valid("378282246310005")
    assert not luhn_valid("4111111111111112")
    assert not luhn_valid("4111 1111")  # digits only
    assert not luhn_valid("")


@pytest.mark.parametrize(
    "text", ["4111111111111111", "4111 1111 1111 1111", "4111-1111-1111-1111", "3782 822463 10005"]
)
def test_card_numbers_found_plain_spaced_and_dashed(text):
    findings = find_pii(f"Paid with {text} yesterday.")

    assert [f["type"] for f in findings] == ["card"]
    assert findings[0]["start"] == len("Paid with ")


def test_luhn_invalid_digit_run_is_not_a_card():
    assert types("Order 4111111111111112 shipped.") == []


@pytest.mark.parametrize(
    "text, kind",
    [
        ("mail cardholder@example.com today", "email"),
        ("call (202) 555-0143", "phone"),
        ("call 202-555-0143", "phone"),
        ("call +1 202.555.0143", "phone"),
        ("SSN 123-45-6789", "ssn"),
    ],
)
def test_other_identifiers_found(text, kind):
    assert types(text) == [kind]


@pytest.mark.parametrize(
    "text",
    [
        "Charged 844.83 instead of 1142.30 USD",
        "Bought on 2026-04-05, refunded 2026-04-20",
        "Case S-0052 and D-0007",
        "Reason codes 10.4, 12.5, 13.1 and 13.6",
        "MCC 5712, MCC 4899",
        "SSN-shaped but never issued: 000-12-3456, 666-12-3456, 912-12-3456",
        "Ten digits with no separators: 2025550143",
    ],
)
def test_ordinary_values_are_not_flagged(text):
    assert find_pii(text) == []


def test_synthetic_dataset_has_no_findings():
    for case in generate_disputes(200, 42):
        assert find_pii(json.dumps(case)) == [], case["case_id"]


@pytest.mark.parametrize("text", ["4111111111111111", "4111 1111 1111 1111", "4111-1111-1111-1111"])
def test_masked_card_never_contains_the_full_number(text):
    (finding,) = find_pii(text)

    assert finding["masked"] == "411111******1111"
    assert VISA_TEST not in finding["masked"]


def test_other_types_are_fully_masked():
    findings = find_pii("cardholder@example.com, 202-555-0143, 123-45-6789")

    assert [f["masked"] for f in findings] == ["[email]", "[phone]", "[ssn]"]


def test_allowlist_hides_only_listed_values():
    unlisted = with_check_digit("400000123456789")
    text = f"{VISA_TEST} and {unlisted}"

    assert [f["masked"] for f in find_pii(text, allow=ALLOWLIST)] == ["400000******7899"]


def test_every_allowlist_entry_is_something_the_scanner_finds():
    # An entry the scanner would not flag anyway is dead weight or a typo.
    for value in ALLOWLIST:
        assert find_pii(value), value


def test_tests_only_use_allowlisted_values():
    for file in sorted((ROOT / "tests").glob("*.py")):
        found = find_pii(file.read_text(encoding="utf-8"), allow=ALLOWLIST)
        assert found == [], (file.name, found)


def test_scan_of_the_repo_is_clean():
    result = run_scan()

    assert result.returncode == 0, result.stdout


def test_scan_fails_on_an_inserted_card_number(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    (data / "clean.jsonl").write_text('{"claim": "charged 84.20"}\n')
    assert run_scan(data).returncode == 0

    (data / "leak.jsonl").write_text(f'{{"claim": "my card {VISA_TEST} was charged"}}\n')
    result = run_scan(data)

    assert result.returncode == 1
    assert "leak.jsonl:1: card 411111******1111" in result.stdout
    assert VISA_TEST not in result.stdout  # allowlisted, but the data scan never allows it
