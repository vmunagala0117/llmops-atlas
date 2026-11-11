import re
from pathlib import Path

import pytest

from atlas.corpus import CODE_SECTIONS, REQUIRED_KEYS, load_rules, sections
from atlas.prompts import REASON_CODES
from atlas.synth import TEMPLATES

RULES_DIR = Path(__file__).resolve().parents[1] / "data" / "rules"
RULES = load_rules(RULES_DIR)
BY_CODE = {r["code"]: r for r in RULES if r["code"] in REASON_CODES}
CODE_PATTERN = re.compile(r"\b1[0-3]\.\d\b")


def neighbours(code):
    text = sections(BY_CODE[code]["body"])["When it does not apply"]
    return set(CODE_PATTERN.findall(text)) - {code}


def test_nine_files_load_with_required_keys():
    assert len(RULES) == 9
    for rule in RULES:
        assert set(REQUIRED_KEYS) <= set(rule), rule["file"]
        assert rule["status"] == "illustrative, not official network rules"


def test_values_are_strings_not_floats_or_dates():
    # Unquoted YAML turns 13.1 into a float and 2026-11-10 into a date.
    for rule in RULES:
        for key in REQUIRED_KEYS:
            assert isinstance(rule[key], str), (rule["file"], key)


def test_every_code_has_exactly_one_file():
    codes = [r["code"] for r in RULES if r["code"] != "all"]

    assert sorted(codes) == sorted(REASON_CODES)
    for code, rule in BY_CODE.items():
        assert rule["title"] == REASON_CODES[code]
        assert rule["file"].startswith(code)


@pytest.mark.parametrize("code", sorted(REASON_CODES))
def test_code_file_has_all_sections_and_a_neighbour(code):
    found = sections(BY_CODE[code]["body"])

    assert set(CODE_SECTIONS) <= set(found)
    assert neighbours(code)
    assert neighbours(code) <= set(REASON_CODES)


def test_rules_name_every_ambiguous_pair_in_the_dataset():
    # Each ambiguous template is decided against its alt code, so the label's
    # rule file must say when that alt code applies instead.
    pairs = {(t.label, t.alt_reason_code) for t in TEMPLATES if t.alt_reason_code}

    for label, alt in pairs:
        assert alt in neighbours(label), f"{label} rules do not mention {alt}"


def test_no_dashes_or_card_numbers():
    for file in RULES_DIR.glob("*.md"):
        text = file.read_text(encoding="utf-8")
        assert "–" not in text and "—" not in text, file.name
        assert not re.search(r"\d{12,}", text), file.name


def test_missing_front_matter_raises(tmp_path):
    (tmp_path / "bad.md").write_text("# no front matter\n")

    with pytest.raises(ValueError, match="bad.md"):
        load_rules(tmp_path)


def test_sections_splits_on_level_two_headings():
    body = "# Title\nintro\n\n## A\none\n\n## B\ntwo\n### sub\nmore"

    assert sections(body) == {"A": "one", "B": "two\n### sub\nmore"}
