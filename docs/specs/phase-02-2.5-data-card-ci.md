# Spec 2.5: Data card and data checks in CI

## Why
Data needs documentation (what it is, how it was made, its limits) and automated checks, like code.

## Requirements
1. `docs/data-card.md`: purpose; sources (generator, seed, version; rules corpus version); schema; counts per code, difficulty and split; known limitations (template variety, repeated items, amounts stored as floats, synthetic phrasing); privacy (synthetic by construction, PII scan result); intended use and not intended for.
2. `scripts/validate_data.py`: schema check for both JSONL files; labels and alt codes valid; split and difficulty shares within tolerance; no case_id duplicates; regenerating with seed 42 reproduces the committed files exactly. Exits 1 on failure.
3. CI: add steps running `scripts/scan_data.py` and `scripts/validate_data.py` (no network, no database).

## Acceptance criteria
- Both scripts exit 0 on the current repo; CI passes.
- Changing one label to an invalid code makes validation fail (test).