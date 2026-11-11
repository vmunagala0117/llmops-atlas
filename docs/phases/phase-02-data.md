# Phase 2: Data

## Goal

Replace the 12 hand-written Phase 1 cases with a larger, reproducible dataset, and keep a held-out split that prompt authors never see.

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

## Open questions and next experiment

- 200 cases from 48 templates is still low variety. A model could score well by recognising template wording. Check whether accuracy on held-out (unseen templates) is clearly lower than on dev.
- Held-out has 50 cases, about 6 per code and 1 ambiguous per code. It is enough to gate overall accuracy, but too small for conclusions per code.
- The held-out templates are readable in `synth.py`. Keeping them out of prompt work is a process rule, not something the code enforces.
- `render()` still prints `amount_usd` as a raw float (`84.2`), while claims use two decimals. Fixing that changes the released prompts, so it needs new versions.
