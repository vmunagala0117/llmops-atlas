# Changelog

All notable changes to this project are recorded here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

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
