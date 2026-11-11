import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
VALIDATE = ROOT / "scripts" / "validate_data.py"
DATA = ROOT / "data" / "synthetic"
DEV = "disputes_dev.jsonl"


def run(*args):
    return subprocess.run(
        [sys.executable, str(VALIDATE), *map(str, args)], capture_output=True, text=True
    )


@pytest.fixture
def data_copy(tmp_path):
    for file in DATA.glob("*.jsonl"):
        shutil.copy(file, tmp_path / file.name)
    return tmp_path


def edit_first_case(folder, **changes):
    path = folder / DEV
    lines = path.read_text().splitlines()
    lines[0] = json.dumps({**json.loads(lines[0]), **changes})
    path.write_text("\n".join(lines) + "\n")


def test_committed_data_is_valid():
    result = run()

    assert result.returncode == 0, result.stdout
    assert "valid: no problems" in result.stdout


def test_invalid_label_fails(data_copy):
    edit_first_case(data_copy, label_reason_code="99.9")

    result = run(data_copy)

    assert result.returncode == 1
    assert f"{DEV}:1: label_reason_code '99.9' is not a valid code" in result.stdout


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"alt_reason_code": "13.6"}, "alt_reason_code set on a standard case"),
        ({"amount_usd": "32.04"}, "amount_usd '32.04' is not a positive number"),
        ({"split": "held_out"}, "split 'held_out' in the dev file"),
        ({"extra": 1}, "unexpected ['extra']"),
    ],
)
def test_schema_problems_are_reported(data_copy, changes, message):
    edit_first_case(data_copy, **changes)

    result = run(data_copy)

    assert result.returncode == 1
    assert message in result.stdout


def test_duplicate_case_id_fails(data_copy):
    second = json.loads((data_copy / DEV).read_text().splitlines()[1])
    edit_first_case(data_copy, case_id=second["case_id"])

    result = run(data_copy)

    assert result.returncode == 1
    assert f"duplicate case_id: ['{second['case_id']}']" in result.stdout


def test_hand_edit_that_stays_valid_still_fails_reproduction(data_copy):
    # A valid-looking change (a new merchant name) is still a hand edit.
    edit_first_case(data_copy, merchant="Quillmere Fuel")

    result = run(data_copy)

    assert result.returncode == 1
    assert f"{DEV}: differs from generate_disputes(200, 42)" in result.stdout
