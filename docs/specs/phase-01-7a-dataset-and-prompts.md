# Spec 7a: Labelled dataset and versioned prompts

## Why
We cannot choose prompts or models without known right answers. This is the seed of the golden set used by the evaluation gate in Phase 6.

## Requirements
1. `data/samples/disputes_v1.jsonl`: 12 synthetic disputes, one JSON object per line.
   Fields: case_id, channel, amount_usd, merchant, mcc, cardholder_claim, label_reason_code.
2. Cover Visa codes 10.4, 12.5, 12.6, 13.1, 13.2, 13.3, 13.6, 13.7 (at least one each).
3. Include 2 deliberately ambiguous cases: 13.2 vs 13.7, and 13.1 vs 13.6.
4. `src/atlas/prompts.py` with:
   - `REASON_CODES`: code to name.
   - `dispute_triage@v1`: zero shot (codes plus output format).
   - `dispute_triage@v2`: v1 plus decision rules and one worked example.
   - Output contract: JSON with reason_code, confidence (0 to 1), summary, missing_evidence (list).
   - `render(prompt_id, case) -> list[dict]` returning system and user messages.

## Acceptance criteria
- Every label in the dataset is a key of REASON_CODES.
- Every prompt renders for every case without error.
- No real names, card numbers or personal data.

## Out of scope
Calling the model, scoring, retrieval.