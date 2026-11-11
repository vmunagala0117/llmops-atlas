# Changelog

All notable changes to this project are recorded here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [0.2.1-data] - 2026-11-11

### Added

- Phase 2 walkthrough notebook `notebooks/02_data_pipeline.ipynb`, run in CI in mock mode with no database.
- `store.describe_target()`, `store.unavailable_reason()`, `store.model_counts()`, `store.nearest()` and `llm.cosine()`.

### Changed

- `store.connect()` gives up after 5 seconds.

## [0.2-data] - 2026-11-11

### Added (Phase 2: data)

- Synthetic dispute generator `generate_disputes(n, seed)` in `src/atlas/synth.py` and `scripts/make_dataset.py`: 200 cases (150 dev, 50 held out) in `data/synthetic/`, with held-out-only templates and `alt_reason_code` on ambiguous cases.
- Rules corpus in `data/rules/` (8 reason codes plus a guide for choosing between them) and its loader, `src/atlas/corpus.py`.
- PII scanner in `src/atlas/pii.py` and `scripts/scan_data.py` (Luhn-checked card numbers, emails, US phone numbers, US SSNs), plus `config/pii_allowlist.txt` for test values.
- `embed()` in `src/atlas/llm.py`, with deterministic vectors in mock mode.
- Rules ingestion into Postgres with pgvector: `src/atlas/chunking.py`, `src/atlas/store.py`, `scripts/ingest_rules.py`, and an optional `docker-compose.yml` on host port 5433.
- Data card `docs/data-card.md` and `scripts/validate_data.py`.
- CI steps for the PII scan and data validation.
- Case study CS-003, the roadmap, and specs 2.1 to 2.5.

### Changed

- `scripts/make_dataset.py` builds its file text in `render_files()`, so validation can compare bytes with a fresh run.

## [0.1-baseline] - 2026-11-10

### Added (Phase 1: baseline copilot and model scorecard)

- `call_model()` in `src/atlas/llm.py`: the single LiteLLM call path, with client-side latency, token and cost capture, default timeout and retries, errors returned as values, and an offline mock mode (`ATLAS_MOCK=1`).
- Versioned prompts `dispute_triage@v1` and `dispute_triage@v2` in `src/atlas/prompts.py`.
- Synthetic dataset `data/samples/disputes_v1.jsonl` (12 cases, eight Visa reason codes).
- Scorecard (`src/atlas/scorecard.py`) and notebook `notebooks/01_baseline_scorecard.ipynb`.
- Offline test suite and GitHub Actions CI (lint, tests, notebook in mock mode).
- Smoke test script for vendor SDK and LiteLLM connectivity.
- README, phase 1 journal and changelog.

### Fixed

- Added `tenacity` to requirements: LiteLLM needs it when `num_retries` is set.
