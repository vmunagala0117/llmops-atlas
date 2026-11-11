# Spec 2.1: Synthetic dispute generator

## Why
12 hand-written cases are too few to trust and were seen while writing prompts. We need a larger, reproducible dataset with a held-out split that prompt authors never inspect.

## Requirements
1. `src/atlas/synth.py` with `generate_disputes(n: int, seed: int) -> list[dict]`.
   - Same seed gives identical output.
   - Fields: case_id, split, channel, amount_usd, merchant, mcc, transaction_date, cardholder_claim, label_reason_code, difficulty (standard | ambiguous), template_id.
   - At least 3 claim templates per reason code, filled with Faker (merchants, amounts, dates) and small variations (tone, extra detail, typos).
   - All 8 reason codes, roughly balanced; about 15% ambiguous cases.
   - Split: 75% dev, 25% held_out, stratified by reason code.
2. `scripts/make_dataset.py` writes `data/synthetic/disputes_dev.jsonl` and `data/synthetic/disputes_heldout.jsonl` (n=200, seed=42), and prints counts per code and split.
3. No real names, card numbers or personal data; merchants are fictional.

## Acceptance criteria
- Tests: determinism (same seed, same output), every label valid, both splits contain all 8 codes, ambiguous share between 10% and 20%.
- Generated files are committed (they are small and reproducible).

## Out of scope
LLM-written claims, rules corpus, embeddings.

## Decisions
Made while planning, before implementation.

1. **Held-out-only templates.** Each reason code has its own held-out templates, used only for `held_out` cases (no `template_id` appears in both splits). With shared templates, anyone who reads dev cases already knows the held-out wording, so held-out would not really be unseen. This way it tests phrasing the prompt author never saw.
2. **Merchants from our own word lists.** Merchant names are made-up first parts plus a category word (for example "Voltway Electronics"), picked with the seeded Faker instance. Faker's `company()` builds names from real surnames ("Johnson LLC") that can match real businesses, which breaks requirement 3. Our own lists are fictional by construction and also keep each name consistent with its MCC. Faker is still used for amounts and dates.
3. **Extra field `alt_reason_code`.** It is the near-miss code for ambiguous cases (for example 13.6 for a 13.1 case) and null for standard cases. Without it, later scoring cannot tell "picked the expected near-miss" from "plain wrong", and those point to different fixes (decision rules versus a basic misunderstanding). This adds a field the spec's list does not have.
4. **Split stratified by reason code and difficulty.** Each split gets about 25% of each code's standard cases and about 25% of its ambiguous cases. Stratifying by code alone could leave held-out with very few ambiguous cases by chance, and those are the cases that best show whether a prompt generalises.
