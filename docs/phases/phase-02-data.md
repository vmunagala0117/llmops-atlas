# Phase 2: Data

## Goal

Replace the 12 hand-written Phase 1 cases with a larger, reproducible dataset, and keep a held-out split that prompt authors never see.

## Summary

- **What the generator does:** `generate_disputes(n, seed)` fills claim templates with fictional merchants, amounts and dates to produce labelled, reproducible disputes for all 8 reason codes, about 15% of them ambiguous, split about 75/25 into dev and held-out.
- **Decisions:** held-out cases use held-out-only templates (no wording leaks from dev), merchant names come from our own word lists (Faker company names use real surnames), ambiguous cases carry `alt_reason_code` (the expected near-miss), and the split is stratified by code and difficulty (so held-out always has every code and some ambiguous cases).

## What I built

- `src/atlas/synth.py`: `generate_disputes(n, seed)` builds labelled disputes from claim templates (spec 2.1).
  - 48 templates: per reason code, 3 dev standard, 1 held-out standard, 1 dev ambiguous and 1 held-out ambiguous.
  - Ambiguous pairs, each decided by one stated fact: 13.1 vs 13.6, 13.2 vs 13.7, 12.5 vs 12.6, 13.3 vs 13.1, 10.4 vs 13.2.
  - Variations: tone (neutral, frustrated, polite), an optional extra sentence that never changes the label, and typos (two letters swapped inside a word, never in digits or the merchant name).
- `scripts/make_dataset.py`: writes `data/synthetic/disputes_dev.jsonl` (150 cases) and `disputes_heldout.jsonl` (50 cases) for n=200, seed=42, and prints counts per code and split. It needs no `.env`.
- `tests/test_synth.py`: determinism, committed files match the generator, valid fields and labels, all 8 codes in both splits, about 25% held out per code, ambiguous share, no template shared between splits, no card-number-like digit runs, 10.4 never in store.

## Decisions

The four design choices are recorded with their reasons in the Decisions section of `docs/specs/phase-02-2.1-synthetic-generator.md`: held-out-only templates, merchants from our own word lists, an extra `alt_reason_code` field, and a split stratified by code and difficulty. In addition:

- **Quotas, not random draws.** The number of cases per code, per difficulty and per split is fixed before any text is written (25 per code, exactly 30 ambiguous, about 25% held out). Tests then check exact properties instead of passing or failing by chance.
- **Determinism.** One seeded `random.Random` and one seeded Faker instance, never the global ones. Dates come from a fixed window (January to June 2026), not from today. Month names come from our own list, because `strftime("%B")` depends on the machine's locale. Running the script under three different `PYTHONHASHSEED` values gives byte-identical files.
- **Faker is pinned** (`faker==40.54.0`). Faker's output for a given seed changes between versions. A test compares the committed files with a fresh run, so an upgrade or a template edit without regenerating fails CI instead of drifting silently.
- **`{date}` is always the disputed transaction**, the same as `transaction_date`. Earlier events (a cancellation) use `{earlier_date}` and later ones (a refund) use `{later_date}`. My first version used `{date}` for the cancellation in 13.2 claims, so `transaction_date` pointed at the wrong event. I caught it by reading sample output.
- **Case ids start with `S-`** so they never collide with the Phase 1 `D-` ids.

## Rules corpus (spec 2.2)

- `data/rules/`: one markdown file per reason code plus `choosing-between-codes.md`, each with YAML front matter (code, title, version, owner, dates, status "illustrative, not official network rules") and four sections. Written in our own words from prompt v2 and the dev templates.
- `src/atlas/corpus.py`: `load_rules(path)` returns front matter plus `body` and `file` per file, sorted by name; `sections(body)` splits on `##` headings.
- Decisions are in the Decisions section of `docs/specs/phase-02-2.2-rules-corpus.md`.

Review table: each neighbour rule and the v2 rule it restates. The test only checks that the right codes are named; this table is for checking the meaning.

| Pair | Deciding fact in the rules | v2 rules |
| --- | --- | --- |
| 13.1 vs 13.6 | Refund confirmed in writing: 13.6. Only mentioned, conditional or by phone: 13.1 | 4, 7 |
| 13.3 vs 13.1 | Something arrived, even the wrong or a cheaper item: 13.3. Nothing arrived: 13.1 | 4, 6 |
| 13.1 vs 13.7 | Cancelled a one-off order before delivery: 13.7 | 4, 8 |
| 13.2 vs 13.7 | Ongoing subscription: 13.2. Only one order, whatever the site calls it: 13.7 | 5, 8 |
| 13.2 vs 10.4 | Signed up (even a forgotten trial) and cancelled: 13.2. Never signed up: 10.4 | 1, 5 |
| 12.5 vs 12.6 | One charge, wrong amount: 12.5. Two charges for one purchase: 12.6 | 2, 3 |
| 10.4 vs 12.5, 12.6 | Cardholder made the purchase: not 10.4 | 1, 2, 3 |
| 13.6 vs 13.2, 13.7 | After cancelling, refund confirmed in writing: 13.6 | 5, 7, 8 |
| 13.3 vs 13.6 | Item returned and refund confirmed in writing: 13.6 | 6, 7 |

Two points go a little beyond v2: 10.4 excludes card-present fraud (outside our 8 codes), and 13.6 covers a confirmed refund whatever the reason (lost order, return, cancellation), which v2 rule 7 implies but does not say.

## PII scanner (spec 2.3)

- `src/atlas/pii.py`: `luhn_valid` and `find_pii(text)`, which finds Luhn-valid card numbers (13 to 19 digits, with optional spaces or dashes), emails, US phone numbers and US SSNs. Each finding has a type, a masked value and a start position.
- `scripts/scan_data.py`: scans `data/` and `docs/` (jsonl, md, csv, txt), prints file:line, type and masked value, and exits 1 on any finding. The current repo is clean.
- `config/pii_allowlist.txt`: the deliberate fake values in `tests/`. Only tests use it; a test fails if `tests/` holds a value that is not listed.
- Decisions are in the Decisions section of `docs/specs/phase-02-2.3-pii-scanner.md`.
- Found while building it: a test that needs one unlisted card number clashes with the rule that `tests/` holds only listed values. The test now builds that number at runtime from a prefix and a computed check digit.

## Open questions and next experiment

- 200 cases from 48 templates is still low variety. A model could score well by recognising template wording. Check whether accuracy on held-out (unseen templates) is clearly lower than on dev.
- Held-out has 50 cases, about 6 per code and 1 ambiguous per code. It is enough to gate overall accuracy, but too small for conclusions per code.
- The held-out templates are readable in `synth.py`. Keeping them out of prompt work is a process rule, not something the code enforces.
- `render()` still prints `amount_usd` as a raw float (`84.2`), while claims use two decimals. Fixing that changes the released prompts, so it needs new versions.
- Luhn is a weak filter: about 1 in 10 random digit runs of the right length pass. Two dates written next to each other with spaces could trip the card rule. A false alarm costs a look; a miss is an incident.
- The scanner does not find names or street addresses. That needs NLP tools such as Presidio (Phase 8).
- The scan runs in tests but is not yet its own CI step (Step 2.5).

## Ingestion (spec 2.4)

- Database: native Postgres with pgvector on 5432 is primary. `docker-compose.yml` is optional: Postgres 17 with pgvector on host port 5433, named volume `atlas_pgdata`, credentials from `.env`.
- `src/atlas/llm.py`: `embed(texts)` through LiteLLM (model from `ATLAS_EMBED_MODEL`), with deterministic hash-seeded unit vectors in mock mode.
- `src/atlas/chunking.py`: `chunk_rules(docs)`, one chunk per `##` section: 38 chunks (8 codes x 4 sections, plus 6 pairs).
- `src/atlas/store.py`: `rule_chunks` table, `upsert_chunks`, `count_chunks`, `stored_hashes`, `stored_models`.
- `scripts/ingest_rules.py`: PII scan, chunk, skip known hashes, embed new only, insert. First run: `found 38, new 38, skipped 0`. Second run: `found 38, new 0, skipped 38`. All 38 rows have `embed_model` set and 1536 dimensions.
- Decisions are in the Decisions section of `docs/specs/phase-02-2.4-ingestion.md`.
- Found while building it: a native Postgres in WSL was already listening on `127.0.0.1:5432`, so `localhost` reached it instead of the container, without any error. Fix: keep the native server as primary, move compose to host port 5433, and have the ingest script print the server it connected to before doing anything.

Open questions:

- Old versions stay in the table. Phase 3 retrieval must filter to the current version of each file, or it will cite superseded rules.
- The intro paragraph of `choosing-between-codes.md` sits before the first `##` and is not ingested. It holds the fallback rule for claims that show neither deciding fact.
- No vector index yet: 38 rows need none. Add one (HNSW) in Phase 3 if the corpus grows.

## Data card and data checks (spec 2.5)

- `docs/data-card.md`: purpose, sources and versions, schema, counts per code, difficulty and split, known limitations, privacy, intended use and not intended for. Every count was computed from the committed files, not copied from the specs.
- `scripts/validate_data.py`: schema, labels and alt codes, held-out share per code (20% to 30%), ambiguous share (10% to 20%), unique case ids, and byte-for-byte reproduction from seed 42. Exits 1 on any problem.
- `scripts/make_dataset.py` now builds its text in `render_files()`, which validation reuses, so "reproduces exactly" means the same bytes, not just the same parsed rows.
- CI runs `scan_data.py` and `validate_data.py` after the tests, with no network and no database.
- `tests/test_validate_data.py` runs the script on a temporary copy: an invalid label, other schema breaks, a duplicate id, and a valid-looking hand edit each make it exit 1.
- Found while building it: my first draft of the data card listed a 13.2 vs 13.7 ambiguous pair. The data has 13.7 vs 13.2 only. Counting from the files caught it.

## Walkthrough notebook

- `notebooks/02_data_pipeline.ipynb`: one section per step (setup, synthetic data, PII scan, rules corpus, chunking, embeddings, database, summary), each starting with what, why and what to look for. Decisions are in `docs/specs/phase-02-notebook.md`.
- Runs in three modes: CI (mock, no database: the database sections are skipped with the reason), live (real similarities and search), and mock with a reachable database (counts shown, search skipped because the vectors are not comparable).
- Live results: the two refund texts are the most similar pair (0.48, against 0.37 and 0.41 with the fraud text). All 38 stored rows use one model. The nearest chunks to "the merchant promised a refund that never arrived" are 13.1 "When it applies", 13.1 "When it does not apply", then 13.6 "When it applies".
- Found while building it: I expected the search to return 13.6 first. By our own rules, a refund that was only promised is 13.1, so the search was right and my expectation was wrong. Also, `ruff check .` lints notebooks, so long lines in a code cell fail CI like any other code.

## Phase 2 result

Tagged `v0.2-data`, plus `v0.2.1-data` for the walkthrough notebook. The project now has 200 reproducible cases with a held-out split, a versioned rules corpus in pgvector, and privacy and data checks that block CI. Phase 3 builds retrieval with citations on top of the store. The items carried forward are listed in `docs/roadmap.md`.
