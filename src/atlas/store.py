"""Postgres and pgvector store for rule chunks (spec 2.4).

Rows are keyed by ``content_hash``: the same hash means the same code, version,
section and text, so a stored row is never updated, only added.
"""

import os

import numpy as np
import psycopg
from dotenv import load_dotenv
from pgvector.psycopg import register_vector
from psycopg.conninfo import conninfo_to_dict

from atlas.llm import EMBED_DIM

load_dotenv()

CREATE_TABLE = f"""
CREATE TABLE IF NOT EXISTS rule_chunks (
    id           bigserial PRIMARY KEY,
    code         text NOT NULL,
    section      text NOT NULL,
    version      text NOT NULL,
    text         text NOT NULL,
    content_hash text NOT NULL UNIQUE,
    embedding    vector({EMBED_DIM}) NOT NULL,
    embed_model  text NOT NULL,
    ingested_at  timestamptz NOT NULL DEFAULT now()
)
"""

INSERT = """
INSERT INTO rule_chunks (code, section, version, text, content_hash, embedding, embed_model)
VALUES (%s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (content_hash) DO NOTHING
"""


CONNECT_TIMEOUT_S = 5


def connect(url: str | None = None) -> psycopg.Connection:
    """Open a connection to ATLAS_DB_URL. Changes nothing; call prepare() before use."""
    url = url or os.environ.get("ATLAS_DB_URL")
    if not url:
        raise RuntimeError("ATLAS_DB_URL is not set")
    return psycopg.connect(url, connect_timeout=CONNECT_TIMEOUT_S)


def describe_target(url: str | None = None) -> str:
    """Host, port and database from ATLAS_DB_URL, without connecting. Never the password."""
    url = url or os.environ.get("ATLAS_DB_URL")
    if not url:
        return "ATLAS_DB_URL is not set"
    parts = conninfo_to_dict(url)
    return f"host={parts.get('host')} port={parts.get('port', 5432)} database={parts.get('dbname')}"


def unavailable_reason(url: str | None = None) -> str | None:
    """None if the database answers and has the table, else a short reason (no secrets)."""
    try:
        with connect(url) as conn:
            table = conn.execute("SELECT to_regclass('rule_chunks')").fetchone()[0]
    except RuntimeError as exc:
        return str(exc)
    except psycopg.Error as exc:
        return f"cannot connect to {describe_target(url)} ({type(exc).__name__})"
    return None if table else "table rule_chunks does not exist; run scripts/ingest_rules.py"


def server_info(conn: psycopg.Connection) -> str:
    """Where this connection points, for logs. Never includes the password."""
    info = conn.info
    version = conn.execute("SHOW server_version").fetchone()[0]
    return f"host={info.host} port={info.port} database={info.dbname} server={version}"


def prepare(conn: psycopg.Connection) -> None:
    """Create the vector extension and the table if missing, and register the vector type."""
    conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
    register_vector(conn)  # needs the extension, so it comes after it
    conn.execute(CREATE_TABLE)


def stored_hashes(conn: psycopg.Connection) -> set[str]:
    return {row[0] for row in conn.execute("SELECT content_hash FROM rule_chunks")}


def stored_models(conn: psycopg.Connection) -> set[str]:
    return {row[0] for row in conn.execute("SELECT DISTINCT embed_model FROM rule_chunks")}


def count_chunks(conn: psycopg.Connection) -> int:
    return conn.execute("SELECT count(*) FROM rule_chunks").fetchone()[0]


def model_counts(conn: psycopg.Connection) -> dict[str, int]:
    rows = conn.execute("SELECT embed_model, count(*) FROM rule_chunks GROUP BY 1 ORDER BY 1")
    return dict(rows.fetchall())


def nearest(conn: psycopg.Connection, vector: list[float], k: int = 3) -> list[dict]:
    """The k chunks closest to ``vector`` by cosine distance. A preview for Phase 3 retrieval."""
    register_vector(conn)
    rows = conn.execute(
        "SELECT code, version, section, embedding <=> %s AS distance"
        " FROM rule_chunks ORDER BY distance LIMIT %s",
        (np.array(vector), k),
    )
    return [dict(zip(("code", "version", "section", "distance"), r, strict=True)) for r in rows]


def upsert_chunks(
    conn: psycopg.Connection, chunks: list[dict], vectors: list[list[float]], embed_model: str
) -> int:
    """Insert chunks with their vectors, skipping hashes already stored. Returns rows added."""
    if len(chunks) != len(vectors):
        raise ValueError(f"{len(chunks)} chunks but {len(vectors)} vectors")
    if not embed_model:
        raise ValueError("embed_model is required")
    for chunk, vector in zip(chunks, vectors, strict=True):
        if len(vector) != EMBED_DIM:
            raise ValueError(f"{chunk['content_hash'][:12]}: {len(vector)} dims, need {EMBED_DIM}")

    added = 0
    with conn.cursor() as cur:
        for chunk, vector in zip(chunks, vectors, strict=True):
            cur.execute(
                INSERT,
                (
                    chunk["code"],
                    chunk["section"],
                    chunk["version"],
                    chunk["text"],
                    chunk["content_hash"],
                    vector,
                    embed_model,
                ),
            )
            added += cur.rowcount
    return added
