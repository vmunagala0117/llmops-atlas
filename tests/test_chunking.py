from pathlib import Path

import pytest

from atlas.chunking import chunk_rules
from atlas.corpus import CODE_SECTIONS, load_rules
from atlas.prompts import REASON_CODES

RULES_DIR = Path(__file__).resolve().parents[1] / "data" / "rules"
DOCS = load_rules(RULES_DIR)
CHUNKS = chunk_rules(DOCS)
KEYS = {"code", "title", "section", "version", "text", "content_hash"}


def doc(**overrides):
    base = {"code": "13.1", "title": "Not Received", "version": "1.0", "body": "## A\none"}
    return {**base, **overrides}


def test_one_chunk_per_section():
    # 8 code files with 4 sections each, plus 6 pairs in choosing-between-codes.md.
    assert len(CHUNKS) == len(REASON_CODES) * len(CODE_SECTIONS) + 6
    for code in REASON_CODES:
        found = [c["section"] for c in CHUNKS if c["code"] == code]
        assert sorted(found) == sorted(CODE_SECTIONS)


def test_chunks_carry_metadata():
    by_code = {d["code"]: d for d in DOCS}
    for chunk in CHUNKS:
        assert set(chunk) == KEYS
        assert chunk["version"] == by_code[chunk["code"]]["version"]
        assert chunk["title"] == by_code[chunk["code"]]["title"]


def test_text_stands_alone():
    chunk = chunk_rules([doc()])[0]

    assert chunk["text"] == "# Not Received\n## A\n\none"


def test_hashes_are_sha256_and_unique():
    hashes = [c["content_hash"] for c in CHUNKS]

    assert len(set(hashes)) == len(hashes)
    assert all(len(h) == 64 and int(h, 16) >= 0 for h in hashes)


def test_hash_is_stable():
    assert chunk_rules([doc()]) == chunk_rules([doc()])


@pytest.mark.parametrize(
    "change", [{"version": "1.1"}, {"code": "13.6"}, {"body": "## A\ntwo"}, {"body": "## B\none"}]
)
def test_hash_changes_with_citable_fields(change):
    before = chunk_rules([doc()])[0]["content_hash"]

    assert chunk_rules([doc(**change)])[0]["content_hash"] != before


def test_empty_sections_are_skipped():
    assert chunk_rules([doc(body="## A\n\n## B\ntwo")])[0]["section"] == "B"
    assert len(chunk_rules([doc(body="## A\n\n## B\ntwo")])) == 1
