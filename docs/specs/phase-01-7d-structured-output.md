# Spec 7d: Structured outputs

## Why
Today the output contract is only an instruction in the prompt, so a model can break it (for example `"12.6.1"`). Spec 7c measures this as `format_error`. Structured outputs prevent it: the request carries a JSON schema and the model API only returns replies that match it. The format then no longer depends on prompt wording, and we can test whether v1 with a schema is as reliable as v2.

## Requirements
1. `src/atlas/prompts.py`: `TRIAGE_SCHEMA`, a versioned JSON schema for the output contract, built from `REASON_CODES`:
   - `reason_code`: string, `enum` of the 8 codes
   - `confidence`: number; `summary`: string; `missing_evidence`: array of strings
   - all four fields required, `additionalProperties: false`
   - a helper that returns the LiteLLM `response_format` value (`{"type": "json_schema", "json_schema": {"name": ..., "schema": ..., "strict": true}}`)
2. No change to `call_model`: `response_format` goes through as a variant parameter, like `reasoning_effort`.
3. Notebook: 4 variants at default reasoning effort: v1 and v2, each with and without the schema. Names say which, for example `dispute_triage@v1 schema=triage@v1`.
4. Before the run, the notebook prints whether LiteLLM reports schema support for the model (`litellm.supports_response_schema`).

## Acceptance criteria
- Offline: a test with a fake `call_model` shows that the variant's `response_format` reaches the call unchanged.
- Offline: the schema's `enum` equals the keys of `REASON_CODES`, and the mock reply validates against it.
- Live: schema variants show `format_error_rate` 0 and `valid_json_rate` 1. If not, the schema was not enforced, and the journal records why.
- The journal compares v1 with a schema against v2 without one, on accuracy, format errors, latency and cost per successful call.

## Risks and open questions
- **Silent drop.** `call_model` uses `drop_params=True`. If the model or API version does not support `json_schema`, LiteLLM may drop it without an error, and the variant quietly becomes the no-schema variant. Requirement 4 and the live criterion are there to catch this.
- **Forced choice.** An `enum` with no escape value forces a code even when the case is unclear. Decide whether the contract needs a value like `needs_review`. That would be a contract change (schema v2 and a new prompt version), not part of this spec.
- **Range limits.** Strict mode may not accept `minimum`/`maximum` on `confidence`. If so, keep 0 to 1 in the field description and check the range in code.
- **Versioning.** The schema is part of the contract, so it gets its own id (`triage@v1`), and scorecard rows record it through the variant name. Changing the schema means a new id, as with prompts.
- **Mock mode cannot test enforcement.** The mock reply ignores the schema, so enforcement is only shown by the live run.
- **Cost and latency.** Constrained decoding can change latency. Compare p50/p95 and cost per successful call, not accuracy alone.

## Out of scope
Changing prompt text, retries on a bad format, `needs_review` handling, evaluation thresholds.
