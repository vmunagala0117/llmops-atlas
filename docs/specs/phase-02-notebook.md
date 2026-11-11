# Spec: Phase 2 walkthrough notebook

## Why
A cell by cell walkthrough to verify and understand each Phase 2 step, and a learning resource to revisit.

## Requirements
`notebooks/02_data_pipeline.ipynb`, one section per step, each starting with a markdown cell (what, why, what to look for):

1. Setup: mock or live mode, embed model, database target (host, port, db; never the password).
2. Synthetic data (2.1): generate n=200 with seed 42; table of counts by code, difficulty and split; show that regenerating gives identical output; list template_ids per split to prove held-out templates never appear in dev; show one standard and one ambiguous case with alt_reason_code.
3. PII scan (2.3): run find_pii on a few sample strings (a test card number, an amount, a reason code, an email); show masked output; run the repo scan and show its result.
4. Rules corpus (2.2): list the 9 documents with front matter (code, version, owner, review_by); print one document's "When it does not apply" section.
5. Chunking (2.4): chunk count; one chunk printed with its metadata and hash; show that changing one word changes the hash.
6. Embeddings (2.4): embed 3 texts (two about refunds, one about fraud); show vector length; cosine similarity table showing the related pair scores highest. In mock mode, note that similarities are meaningless.
7. Database (2.4): if ATLAS_DB_URL is reachable, show row count, embed_model values, and a preview: the 3 nearest chunks to "the merchant promised a refund that never arrived". Otherwise print why the section is skipped.
8. Summary: what Phase 2 produced and what Phase 3 will use.

## Acceptance criteria
- Runs top to bottom with ATLAS_MOCK=1 and no database (CI).
- Runs live against your database and embedding deployment.
- No logic defined in the notebook beyond display code.
## Decisions

1. **New helpers live in `src/atlas/`, not in the notebook.** `store.describe_target()` shows host, port and database from the URL without connecting and never shows the password. `store.unavailable_reason()` returns why the database can't be used, or None. `store.model_counts()` and `store.nearest()` (a cosine search preview for Phase 3) are also new, along with `llm.cosine()`. The notebook keeps only display code and the `if` that picks what to show.
2. **`connect()` now has a 5 second connect timeout**, so a missing database makes section 7 skip quickly instead of hanging.
3. **Search is skipped when the stored model differs from this run's.** Mock mode with a reachable live database still shows row counts, but it does not compare hash-based vectors with real ones.
4. **The test card number is read from `config/pii_allowlist.txt`.** Spec 2.3 keeps card-like literals to `tests/` and `config/`, and the notebook prints only labels and masked findings, never the raw sample.
5. **Committed without outputs**, like notebook 01, so live results and local paths never land in git. CI executes it in mock mode with no database.
6. **What the search preview showed.** The live preview for "the merchant promised a refund that never arrived" returns 13.1 first, then 13.6. That matches the rules: a refund that was only promised is 13.1. I first expected 13.6 and corrected the notebook text after the live run.
