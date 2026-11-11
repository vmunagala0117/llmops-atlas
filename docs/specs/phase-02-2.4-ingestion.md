# Spec 2.4: Ingest the rules corpus into pgvector

## Why
Phase 3 retrieves rule sections by meaning and cites them. Ingestion must be traceable (metadata), repeatable (idempotent) and privacy checked.

## Requirements
1. Database: the primary store is a native Postgres with pgvector on port 5432, reached through `ATLAS_DB_URL` in `.env`. `docker-compose.yml` is an optional alternative: Postgres with pgvector on host port 5433 (so it never clashes with the native server), named volume, credentials from `.env`, never hardcoded. Compose users point `ATLAS_DB_URL` at port 5433. `scripts/ingest_rules.py` prints the server it connected to (host, port, database, server version, never the password) before doing anything else.
2. `src/atlas/llm.py`: add `embed(texts: list[str]) -> list[list[float]]` via LiteLLM, model from ATLAS_EMBED_MODEL. In ATLAS_MOCK=1, return deterministic fake vectors (derived from a hash of the text), no network.
3. `src/atlas/chunking.py`: `chunk_rules(docs) -> list[dict]`, one chunk per `##` section, with code, title, section, version, text, content_hash (sha256).
4. `src/atlas/store.py`: create table `rule_chunks` (id, code, section, version, text, content_hash UNIQUE, embedding vector(1536), embed_model, ingested_at); `upsert_chunks(chunks, vectors)`; `count_chunks()`.
5. `scripts/ingest_rules.py`: run the PII scan first and stop if it fails; load rules, chunk, skip hashes already stored, embed new chunks only, upsert, print counts (found, new, skipped).

## Acceptance criteria
- Offline tests: chunking (sections, metadata, hashes), mock embeddings deterministic and 1536 long.
- Running ingestion twice: second run reports 0 new chunks.
- Every stored row has embed_model set.

## Out of scope
Search and retrieval (Phase 3), hybrid keyword search.

## Decisions

1. **Compose reads `POSTGRES_USER`, `POSTGRES_PASSWORD` and `POSTGRES_DB` from `.env`.** Compose cannot split a URL into parts, so these sit next to `ATLAS_DB_URL` and must match it. Compose fails to start if any is missing, instead of falling back to a default password.
2. **`embed()` raises; `call_model()` does not.** A failed call in a scorecard run is one bad row. A failed embedding during ingestion would leave a half-filled store, so it stops the run. It also checks that every vector has 1536 dimensions before anything is stored.
3. **Mock vectors are labelled `atlas-mock-embed`.** In mock mode, `embed_model` is stored as that name, never as the real model, so fake vectors can never pass as real ones.
4. **One embedding model per table.** The script stops if the table holds vectors from a model other than the current one. Vectors from different models are not comparable. Changing models means a new table or a rebuild.
5. **The chunk text repeats the doc title and the section heading** (`# title`, `## section`, then the body), so a retrieved chunk still makes sense without its file.
6. **The hash covers code, version, section and text.** Bumping a file's `version` creates new chunks, and the old ones stay so old citations (`code@version`) still resolve.
7. **Insert, never update.** The same hash means the same content, so `ON CONFLICT (content_hash) DO NOTHING`. The script also skips known hashes before embedding, so a second run costs no API calls.
8. **Store functions take a connection** (`upsert_chunks(conn, chunks, vectors, embed_model)`), so the caller controls the transaction, and the input checks run before any SQL (tested offline).
9. **The PII gate runs `scripts/scan_data.py` as a subprocess**, so ingestion uses exactly the same check and exit code as the standalone scan.
10. **Native Postgres on 5432 is primary; compose uses host port 5433.** A native Postgres in WSL already listened on `127.0.0.1:5432`, so `localhost:5432` reached it instead of the container, with no error. Giving the container its own port makes the choice explicit in `ATLAS_DB_URL`, and printing the server before ingesting makes a wrong target visible.
