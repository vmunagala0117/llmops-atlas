# CS-001: The 67% accuracy that was not an accuracy problem

**Phase:** 1 · **Date:** 2026-11-10 · **Status:** Measured and specified; prevention pending (spec 7d)

## Context
The Dispute Copilot classifies card disputes into one of eight Visa reason codes and returns JSON. The Phase 1 scorecard compares prompt versions and settings on 12 labelled synthetic cases.

## Symptom
The first live run showed prompt v1 at 67% accuracy (default reasoning) and 58% (minimal reasoning). Prompt v2 scored 100% on both. The obvious conclusion was "v1 reasons worse".

## Investigation
1. Read the misses table instead of trusting the summary number.
2. Compared predicted and label for every miss. Most predictions were the right code plus its title, for example `10.4: Other Fraud: Card-Absent Environment` instead of `10.4`.
3. Counted genuine misclassifications separately. Only one remained: D-0007, an ambiguous case (13.1 vs 13.6) predicted as 13.6.
4. Asked why v2 had no such errors. v2 contains a worked example showing the exact output; v1 only describes the format.

| Variant | Reported accuracy | Real classification accuracy | Format errors |
| --- | --- | --- | --- |
| v1, default | 67% | 92% | 3 |
| v1, minimal | 58% | 100% | 5 |
| v2, default | 100% | 100% | 0 |
| v2, minimal | 100% | 100% | 0 |

## Root cause
The output contract was described in the prompt but not enforced anywhere. The scorer used exact matching, which is correct, but it could not tell "wrong format" from "wrong answer", so both showed up as lower accuracy.

## Fix: steps taken
1. **Measure it separately.** Added a `format_error` flag (valid JSON, but `reason_code` is not exactly one of the eight codes) and a format error rate in the summary, kept separate from accuracy. A test covers the `10.4: Other Fraud` case.
2. **Keep the strict scoring.** Exact matching stays. Loosening the scorer would hide the defect from downstream systems, which also need the bare code.
3. **Prevent it at the source.** Wrote spec 7d: structured outputs, a JSON schema that restricts `reason_code` to the eight allowed values, enforced by the model API rather than by prompt wording. It is added as a variant parameter, so its effect is measured, not assumed.
4. **Recorded the decision** in the phase journal: v2 with minimal reasoning is the production candidate, with format enforcement to follow.

## Result
- Format and reasoning failures are now reported separately, so a format defect can no longer be mistaken for a prompt quality problem.
- Pending: spec 7d results (does schema enforcement bring v1 to zero format errors?).

## Lessons
- Read the misses, not just the averages.
- Few-shot examples mainly fix format adherence, not reasoning.
- Contracts belong in the system (schema, validation), not only in prompt wording.
- Different failure types have different owners and fixes, so measure them separately.

## Caveats
12 cases; one case moves accuracy by about 8 points. v2's rules were written with these cases in view; held-out cases come in Phase 6.

## Summary
"Our first scorecard showed one prompt at 67% accuracy. Instead of rewriting the prompt, I read the misses. Most were the right code with extra text attached, so it was a format problem, not a reasoning problem. I separated format errors from accuracy in the scorecard, kept strict scoring because downstream systems need the exact code, and specified schema-enforced structured outputs so the contract is guaranteed by the platform rather than by prompt wording. The lesson I'd bring to a platform team: measure failure types separately, because they have different fixes."