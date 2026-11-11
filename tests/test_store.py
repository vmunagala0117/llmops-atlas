import pytest

from atlas import store
from atlas.llm import EMBED_DIM

CHUNK = {"code": "13.1", "section": "A", "version": "1.0", "text": "t", "content_hash": "h" * 64}


# These checks run before any database call, so no connection is needed.
def test_upsert_rejects_mismatched_lengths():
    with pytest.raises(ValueError, match="1 chunks but 0 vectors"):
        store.upsert_chunks(None, [CHUNK], [], "openai/atlas-test-embed")


def test_upsert_rejects_wrong_dimensions():
    with pytest.raises(ValueError, match="need 1536"):
        store.upsert_chunks(None, [CHUNK], [[0.0] * 3], "openai/atlas-test-embed")


def test_upsert_requires_embed_model():
    with pytest.raises(ValueError, match="embed_model"):
        store.upsert_chunks(None, [CHUNK], [[0.0] * EMBED_DIM], "")


def test_table_enforces_metadata():
    sql = store.CREATE_TABLE
    assert "content_hash text NOT NULL UNIQUE" in sql
    assert f"vector({EMBED_DIM})" in sql
    assert "embed_model  text NOT NULL" in sql
