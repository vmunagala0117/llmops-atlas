# Spec 7b: Model and prompt scorecard

## Why
Decisions about prompts, models and settings must be measured on our own cases, with quality and cost side by side.

## Requirements
1. `src/atlas/parsing.py`: `parse_reply(text) -> dict | None` extracts the first JSON object from a reply; returns None if missing or invalid.
2. `src/atlas/scorecard.py`:
   - `load_cases(path) -> list[dict]`
   - `run_experiment(variants, cases) -> DataFrame`. A variant is {name, prompt_id, model, params}. Calls `call_model` only. One row per (variant, case): correct, valid_json, predicted, label, prompt/completion/reasoning tokens, cost_usd, latency_ms, error.
   - `summarize(df) -> DataFrame` per variant: accuracy, valid_json_rate, error_rate, p50 and p95 latency, mean reasoning tokens, cost per 1,000 requests.
   - Calls run one after another (respect our low token-per-minute quota).
3. `notebooks/01_baseline_scorecard.ipynb`, thin: load cases; run 4 variants (v1 and v2, each with default and reasoning_effort "minimal") on the model from ATLAS_MODELS; show summary and the misses table; save both to `results/` with a UTC timestamp.

## Acceptance criteria
- With ATLAS_MOCK=1 the notebook runs end to end with no network.
- A failed call is counted in error_rate, not raised.

## Out of scope
CI, evaluation thresholds, MLflow.