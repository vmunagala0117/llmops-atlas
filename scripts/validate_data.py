"""Validate the committed synthetic datasets (spec 2.5).

Usage: python scripts/validate_data.py [DATA_DIR]

Checks both JSONL files in data/synthetic/ (or DATA_DIR): schema, valid labels
and alt codes, split and difficulty shares, unique case ids, and that
regenerating with the committed seed reproduces the files byte for byte.
Prints one line per problem and exits 1 if there are any. Needs no .env, no
network and no database.
"""

import datetime as dt
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from make_dataset import FILES, SEED, N, render_files  # noqa: E402

from atlas.prompts import REASON_CODES  # noqa: E402
from atlas.synth import generate_disputes  # noqa: E402

DATA_DIR = ROOT / "data" / "synthetic"
STRING_FIELDS = ("case_id", "merchant", "mcc", "cardholder_claim", "template_id")
FIELDS = set(STRING_FIELDS) | {
    "split",
    "difficulty",
    "channel",
    "amount_usd",
    "transaction_date",
    "label_reason_code",
    "alt_reason_code",
}
CHANNELS = {"online", "in_store", "phone"}
DIFFICULTIES = {"standard", "ambiguous"}
CASE_ID = re.compile(r"S-\d{4}")
MCC = re.compile(r"\d{4}")
HELD_OUT_SHARE = (0.20, 0.30)  # per code
AMBIGUOUS_SHARE = (0.10, 0.20)  # overall


def _is_date(value) -> bool:
    try:
        dt.date.fromisoformat(value)
    except (TypeError, ValueError):
        return False
    return True


def check_case(case: dict, split: str) -> list[str]:
    """Problems with one case read from the ``split`` file."""
    if set(case) != FIELDS:
        missing, extra = sorted(FIELDS - set(case)), sorted(set(case) - FIELDS)
        return [f"fields: missing {missing}, unexpected {extra}"]

    problems = []
    for field in STRING_FIELDS:
        if not isinstance(case[field], str) or not case[field]:
            problems.append(f"{field} is not a non-empty string")
    if isinstance(case["case_id"], str) and not CASE_ID.fullmatch(case["case_id"]):
        problems.append(f"case_id {case['case_id']!r} is not S-NNNN")
    if isinstance(case["mcc"], str) and not MCC.fullmatch(case["mcc"]):
        problems.append(f"mcc {case['mcc']!r} is not 4 digits")
    if case["split"] != split:
        problems.append(f"split {case['split']!r} in the {split} file")
    if case["difficulty"] not in DIFFICULTIES:
        problems.append(f"difficulty {case['difficulty']!r} is not valid")
    if case["channel"] not in CHANNELS:
        problems.append(f"channel {case['channel']!r} is not valid")
    amount = case["amount_usd"]
    if isinstance(amount, bool) or not isinstance(amount, int | float) or amount <= 0:
        problems.append(f"amount_usd {amount!r} is not a positive number")
    if not _is_date(case["transaction_date"]):
        problems.append(f"transaction_date {case['transaction_date']!r} is not an ISO date")

    label, alt = case["label_reason_code"], case["alt_reason_code"]
    if label not in REASON_CODES:
        problems.append(f"label_reason_code {label!r} is not a valid code")
    if case["difficulty"] == "standard" and alt is not None:
        problems.append("alt_reason_code set on a standard case")
    if case["difficulty"] == "ambiguous" and (alt not in REASON_CODES or alt == label):
        problems.append(f"alt_reason_code {alt!r} is not a valid code other than the label")
    return problems


def check_shares(cases: list[dict]) -> list[str]:
    problems = []
    per_code = Counter(c["label_reason_code"] for c in cases)
    held = Counter(c["label_reason_code"] for c in cases if c["split"] == "held_out")
    for code in REASON_CODES:
        for split in ("dev", "held_out"):
            if not any(c["label_reason_code"] == code and c["split"] == split for c in cases):
                problems.append(f"{split} has no {code} cases")
        if per_code[code]:
            share = held[code] / per_code[code]
            if not HELD_OUT_SHARE[0] <= share <= HELD_OUT_SHARE[1]:
                problems.append(f"{code}: held-out share {share:.0%} outside {HELD_OUT_SHARE}")

    if cases:
        share = sum(c["difficulty"] == "ambiguous" for c in cases) / len(cases)
        if not AMBIGUOUS_SHARE[0] <= share <= AMBIGUOUS_SHARE[1]:
            problems.append(f"ambiguous share {share:.0%} outside {AMBIGUOUS_SHARE}")

    duplicates = [i for i, n in Counter(c["case_id"] for c in cases).items() if n > 1]
    if duplicates:
        problems.append(f"duplicate case_id: {sorted(duplicates)}")
    return problems


def validate(data_dir: Path) -> list[str]:
    """Every problem found, as printable lines. Empty means valid."""
    problems: list[str] = []
    cases: list[dict] = []
    for split, name in FILES.items():
        path = data_dir / name
        if not path.is_file():
            problems.append(f"{name}: missing")
            continue
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            try:
                case = json.loads(line)
            except json.JSONDecodeError as exc:
                problems.append(f"{name}:{line_no}: not JSON ({exc.msg})")
                continue
            if not isinstance(case, dict):
                problems.append(f"{name}:{line_no}: not a JSON object")
                continue
            problems += [f"{name}:{line_no}: {p}" for p in check_case(case, split)]
            cases.append(case)

    if not problems:  # shares on malformed rows would only repeat the errors above
        problems += check_shares(cases)

    for name, text in render_files(generate_disputes(N, SEED)).items():
        path = data_dir / name
        if path.is_file() and path.read_text(encoding="utf-8") != text:
            problems.append(
                f"{name}: differs from generate_disputes({N}, {SEED}); "
                "run python scripts/make_dataset.py, never edit by hand"
            )
    return problems


def main(argv) -> int:
    data_dir = Path(argv[0]) if argv else DATA_DIR
    problems = validate(data_dir)
    for problem in problems:
        print(problem)
    print(f"{len(problems)} problem(s)" if problems else "valid: no problems")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
