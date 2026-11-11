# Spec 2.2: Rules knowledge base

## Why
Phase 3 retrieves rules so answers can cite them. The corpus is a governed asset: versioned, owned, reviewable, and clearly illustrative.

## Requirements
1. `data/rules/` with one markdown file per reason code (8 files) plus `choosing-between-codes.md`.
2. YAML front matter: code, title, version, owner, effective_date, review_by, status ("illustrative, not official network rules").
3. Sections: When it applies; When it does not apply (naming neighbouring codes); Evidence the analyst should request; Time limits (illustrative).
4. Written in our own words; no text copied from any card network rulebook.
5. `src/atlas/corpus.py`: `load_rules(path) -> list[dict]` returning metadata plus body for each file.

## Acceptance criteria
- Tests: 9 files load; every reason code in REASON_CODES has exactly one file; required front matter keys present; each code file names at least one neighbouring code under "When it does not apply".
- The neighbour rules agree with the decision rules in prompt v2 (no contradictions).

## Out of scope
Chunking, embeddings, retrieval.

## Decisions

1. **Agreement with v2 is a test plus a review.** A test checks that for every ambiguous template in `synth.py`, the label's file names the template's `alt_reason_code` under "When it does not apply". Whether the prose says the same as v2 cannot be tested, so the phase journal has a table mapping each neighbour rule to its v2 rule for review.
2. **Rules files are versioned like prompts.** A file is released once merged to main. Any later change bumps `version` and `effective_date`, so Phase 3 citations can record `code@version`.
3. **Time limits are invented round numbers** (90 days, 15 days), and each section says so, so nobody mistakes them for real network limits.
4. **PyYAML is pinned** (`pyyaml==6.0.3`) rather than relying on it arriving through other packages. All front matter values are quoted strings, because unquoted `13.1` parses as a float and an unquoted date as a date object; a test checks this.
5. **`choosing-between-codes.md` has `code: "all"`** and the same other keys. It is left out of the one-file-per-code check.
6. **Written from v2 and the dev templates only**, never from the held-out templates, because Phase 3 will put these rules into prompts.
