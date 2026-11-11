"""Ingest the rules corpus into pgvector (spec 2.4).

Usage: python scripts/ingest_rules.py

Steps: print the server it connected to (never the password), PII scan (stop if
it fails), load data/rules, chunk, skip hashes already
stored, embed new chunks only, insert, print counts. Safe to run again: a second
run with no rule changes embeds nothing. Needs ATLAS_DB_URL and, unless
ATLAS_MOCK=1, ATLAS_EMBED_MODEL and API settings in .env.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from atlas import store  # noqa: E402
from atlas.chunking import chunk_rules  # noqa: E402
from atlas.corpus import load_rules  # noqa: E402
from atlas.llm import embed, embed_model_name  # noqa: E402

RULES_DIR = ROOT / "data" / "rules"
SCAN = ROOT / "scripts" / "scan_data.py"


def main() -> int:
    with store.connect() as conn:
        # Say where we are first: a native Postgres and a container can share a port.
        print(f"connected: {store.server_info(conn)}", flush=True)

        # Same gate as the standalone scan: data/ and docs/, no allowlist.
        if subprocess.run([sys.executable, str(SCAN)], check=False).returncode != 0:
            print("PII scan failed: nothing ingested")
            return 1

        chunks = chunk_rules(load_rules(RULES_DIR))
        model = embed_model_name()

        store.prepare(conn)
        others = store.stored_models(conn) - {model}
        if others:
            # Vectors from different models are not comparable, so never mix them.
            print(f"table holds vectors from {sorted(others)}, not {model}: nothing ingested")
            return 1

        known = store.stored_hashes(conn)
        new = [c for c in chunks if c["content_hash"] not in known]
        vectors = embed([c["text"] for c in new]) if new else []
        added = store.upsert_chunks(conn, new, vectors, model)
        total = store.count_chunks(conn)

    print(f"found {len(chunks)}, new {added}, skipped {len(chunks) - len(new)}, stored {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
