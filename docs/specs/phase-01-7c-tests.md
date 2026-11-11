# Spec 7c: Offline tests for Phase 1

## Why
Tests run on every change, so they must be fast, free and offline. They check our logic; model quality is measured by the scorecard.

## Requirements
1. `tests/test_prompts.py`: labels are valid codes; every prompt renders for every case; the claim text appears in the user message.
2. `tests/test_parsing.py`: JSON wrapped in prose is extracted; invalid or missing JSON returns None.
3. `tests/test_scorecard.py`: with a fake call_model (monkeypatch), summarize returns one row per variant with the required columns; a variant whose calls all fail shows error_rate 1.0.
4. Output contract is measured: each row has `format_error` (valid JSON with a reason_code that is not exactly one of the 8 codes, kept separate from `correct`), and summarize reports `format_error_rate`.

## Acceptance criteria
- `pytest -q` and `ruff check .` pass with no network and no .env.