# Phase 1: Baseline copilot and model scorecard

## Goal

Prove that Atlas can reach a hosted model through both the vendor SDK and LiteLLM, and record a first baseline of tokens, latency and cost. Later phases measure every change against this baseline.

## Concepts

- **Tokens.** Models read and write in tokens, not words, and billing counts input (prompt) and output (completion) tokens separately. A one-word reply still costs several output tokens.
- **Reasoning tokens.** Reasoning models "think" before they answer. That thinking is billed as output tokens but never shown in the reply, so a reply can look tiny while the bill is not.
- **TTFT vs total latency.** Time to first token (TTFT) is how long until the first piece of the answer arrives; total latency is how long until the last one. With streaming, TTFT is what a user feels. For batch work like classifying disputes, total latency and cost matter more.
- **Why a portable API matters.** If every call goes through one provider-agnostic interface, switching models or vendors becomes a config change instead of a code rewrite. It also gives one place to add logging, cost tracking and test doubles.

## What I built

- Smoke test that reaches gpt-5-mini through the vendor SDK and through LiteLLM (`scripts/smoke_test.py`). It sends "Reply with one word: ready" and prints the reply, token usage and, for LiteLLM, the estimated cost.
- `call_model()` in `src/atlas/llm.py`: the one path for every model call, with client-side latency, tokens, reasoning tokens, cost, default timeout and retries, and errors returned as values.
- Versioned prompts `dispute_triage@v1` (zero-shot) and `@v2` (decision rules plus one example) in `src/atlas/prompts.py`.
- 12 synthetic disputes in `data/samples/disputes_v1.jsonl`. Two are ambiguous on purpose:
  - `D-0007`: tracking says delivered, merchant promised a refund only if the courier confirms the loss. 13.1 vs 13.6, labelled 13.1 because no refund was confirmed.
  - `D-0009`: a meal kit order cancelled before shipping, on a site that calls it a subscription. 13.2 vs 13.7, labelled 13.7 because there was only ever one order.
- Scorecard (`src/atlas/scorecard.py`, with reply parsing in `src/atlas/parsing.py`) and `notebooks/01_baseline_scorecard.ipynb`, comparing v1/v2 with default and minimal reasoning effort. Each run saves per-case and summary CSVs with a UTC timestamp, so runs never overwrite each other.
- CI that runs lint, tests and the notebook in mock mode on every pull request.

## Results

First run, 2026-11-09. Both paths answered "ready". Latency figures are server-reported (`latency_checkpoint` in the usage payload), not measured on the client, and the calls were not streamed.

| Metric | Vendor SDK | LiteLLM |
| --- | --- | --- |
| Prompt tokens | 12 | 12 |
| Completion tokens | 10 | 74 |
| of which reasoning tokens | 0 | 64 |
| Total tokens | 22 | 86 |
| Service TTFT (ms) | 505 | 273 |
| Service total latency (ms) | 874 | 824 |
| Estimated cost (USD) | not reported | 0.000151 |

Wall time for the whole script was about 11.7 s, but most of that is Python startup and importing libraries, not the model calls.

## Decisions

- Chat Completions through LiteLLM rather than the Responses API: Chat Completions is the format LiteLLM normalizes across providers, so the same call shape works if we switch models or vendors. The Responses API is specific to one vendor and would tie the code to it.
- A prompt version counts as released once it is merged to main. Until then it can still be edited on its branch; after that, any change means a new version.
- The v2 tie-breaker is a general rule ("choose the code whose conditions the claim actually shows"), not one that names the answers to `D-0007` and `D-0009`. A prompt written around the test cases would win on them by construction and inflate its score.
- Every test runs in mock mode through an autouse fixture in `tests/conftest.py`, rather than relying on each test or CI job to set `ATLAS_MOCK=1`: a test someone forgets to mark can never reach a real model, spend money or need the API key.
- The scorecard records one row per case, not just totals: misses stay inspectable, and the summary is a simple group by on that table.
- Mock and live scorecard CSVs get different file names (`_mock`, `_live`), and mock ones are git-ignored, so a CI or test run can never overwrite real results. An earlier blanket `results/` ignore rule also hid live results; it was removed.
- The parser returns the first JSON object in a reply (trying each `{` in turn), not the span from the first `{` to the last `}`, which breaks when a reply contains two objects. Requiring a `reason_code` is a scorecard rule, so it lives in the scorecard, not the parser.
- In mock mode `call_model` replies with a valid answer in the output format (always 13.1), so CI runs parsing and scoring too, not only the call. Mock accuracy is meaningless: it is just the share of cases labelled 13.1.
- An unknown price is recorded as NaN, not 0, so a model missing from LiteLLM's price list reads as unknown rather than free. The summary's cost columns skip NaN, and are NaN when no call was priced.
- Each row has `format_error`: valid JSON whose `reason_code` is not exactly one of the 8 codes (for example `"12.6.1"`). It is kept separate from `correct`, so a format problem never looks like a reasoning problem. Preventing it with structured outputs is the next experiment (spec 7d).
- Variant names must be unique. The summary groups by name, so two variants with the same name would silently be averaged into one row.
- Calls run one after another, with an optional pause (`ATLAS_CALL_DELAY_S`, default 0) for a low token-per-minute quota. Otherwise rate-limit errors would count against the prompt, when the real cause is the quota.
- The notebook uses the first model in `ATLAS_MODELS`. Comparing models is a later experiment.
- The summary reports `n_success` (calls with no provider error) and `cost_per_1k_success_usd` (total spend divided by successful calls). Failed calls cost 0, so the plain average makes a flaky variant look cheaper than it is.

## Open questions and next experiment

- Does lower reasoning effort keep accuracy while cutting cost?
- Is `reasoning_effort="minimal"` actually applied? `call_model` uses `drop_params=True`, so an unsupported setting is dropped silently. If the minimal and default variants show the same reasoning tokens, it probably was not. The notebook now prints this check on live runs.
- Latency includes failed calls, so one timeout lifts p95 a lot. Decide whether to report latency for successful calls only as well.
- Why did the same prompt use 0 reasoning tokens on the SDK path and 64 on the LiteLLM path? Check whether `ATLAS_MODELS` points to the same deployment, and rerun a few times to see how much reasoning varies between runs.
- Add client-side timing (and streaming) so TTFT and total latency are measured from our side, not only reported by the service.

## Review questions

- Why do reasoning models cost more than their answer length suggests?
  Because hidden reasoning tokens are billed as output. In this run, a one-word answer used 74 completion tokens, and 64 of them were reasoning.
