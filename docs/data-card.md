# Data card: synthetic card disputes and rules corpus

**Version:** v0.2-data · **Date:** 2026-11-11 · **Owner:** Atlas project (learning project)

## Purpose

Labelled card disputes for building and evaluating the Dispute Resolution Copilot, which maps a cardholder's free-text claim to one of eight Visa reason codes. The dev split is for prompt and model work. The held-out split is for checking that results carry over to wording the prompt author never saw.

## Sources

| Asset | Files | How it was made | Version |
| --- | --- | --- | --- |
| Synthetic disputes | `data/synthetic/disputes_dev.jsonl`, `disputes_heldout.jsonl` | `generate_disputes(n=200, seed=42)` in `src/atlas/synth.py`, written by `scripts/make_dataset.py` | Generator from spec 2.1, Faker 40.54.0 (pinned) |
| Phase 1 samples | `data/samples/disputes_v1.jsonl` | 12 cases written by hand | v1 |
| Rules corpus | `data/rules/*.md` (9 files) | Written in our own words from prompt v2 and the dev templates (spec 2.2) | Every file at `version: "1.0"` |

The generator fills 48 claim templates with merchants built from our own word lists, amounts and dates. No data was collected from people or copied from real sources. The rules are illustrative and are not official network rules.

## Schema

One JSON object per line, 12 fields:

| Field | Type | Values |
| --- | --- | --- |
| `case_id` | string | `S-0001` to `S-0200`, unique across both files |
| `split` | string | `dev` or `held_out`, and must match the file |
| `difficulty` | string | `standard` or `ambiguous` |
| `channel` | string | `online`, `in_store` or `phone` |
| `amount_usd` | number | Positive, stored as a JSON float (see limitations) |
| `merchant` | string | Fictional name, prefix plus category |
| `mcc` | string | 4-digit merchant category code |
| `transaction_date` | string | ISO date in the window 2026-01-01 to 2026-06-30 |
| `cardholder_claim` | string | Free-text claim |
| `label_reason_code` | string | One of 10.4, 12.5, 12.6, 13.1, 13.2, 13.3, 13.6, 13.7 |
| `alt_reason_code` | string or null | The expected near-miss code on ambiguous cases, null on standard cases |
| `template_id` | string | The template the claim came from, for example `12.6-a` |

## Counts

200 cases: 150 dev, 50 held out. 30 ambiguous (15%).

| Code | Dev standard | Dev ambiguous | Held-out standard | Held-out ambiguous | Total |
| --- | ---: | ---: | ---: | ---: | ---: |
| 10.4 | 16 | 3 | 5 | 1 | 25 |
| 12.5 | 16 | 3 | 5 | 1 | 25 |
| 12.6 | 16 | 3 | 5 | 1 | 25 |
| 13.1 | 16 | 3 | 5 | 1 | 25 |
| 13.2 | 16 | 3 | 5 | 1 | 25 |
| 13.3 | 16 | 3 | 5 | 1 | 25 |
| 13.6 | 16 | 2 | 6 | 1 | 25 |
| 13.7 | 16 | 2 | 6 | 1 | 25 |
| **Total** | **128** | **22** | **42** | **8** | **200** |

Ambiguous pairs (label vs alt code), 3 or 4 cases each: 13.1 vs 13.6, 13.6 vs 13.1, 13.7 vs 13.2, 12.5 vs 12.6, 12.6 vs 12.5, 13.3 vs 13.1, 10.4 vs 13.2, 13.2 vs 10.4.

Channels: 115 online, 49 in store, 36 phone. The rules corpus becomes 38 retrieval chunks (8 codes x 4 sections, plus 6 pairs in `choosing-between-codes.md`).

## Known limitations

- **Low template variety.** 200 cases come from 48 templates (6 per code). A model can score well by recognising template wording. Held-out templates are never used in dev, so a gap between dev and held-out accuracy shows this.
- **Repeated items and merchants.** Retail categories have 4 items each and service categories 1, so the same products recur. There are 115 distinct merchants for 200 cases, and the most common one appears 6 times.
- **Amounts are stored as floats.** `amount_usd` is a JSON number, so 21 cases read like `84.2` rather than `84.20`, while the claims always use two decimals. `render()` prints the raw float into prompts. Fixing this changes released prompts, so it needs new prompt versions.
- **Synthetic phrasing.** Claims are tidier and shorter than real ones. The only noise is tone, one optional extra sentence and simple typos (two letters swapped). There is no slang, no other language, no claim that mixes several problems, and nothing in the transaction data that contradicts the claim.
- **Small held-out split.** About 6 cases per code and 1 ambiguous case per code. It can gate overall accuracy, but it is too small for conclusions per code.
- **Held-out isolation is a process rule.** The held-out templates can be read in `synth.py`. Nothing in the code stops a prompt author from looking.
- **Fixed date window.** All dates fall in the first half of 2026, so the time limits in the rules are never tested against old transactions.

## Privacy

- **Synthetic by construction.** Merchants come from our own word lists, not Faker company names (Faker builds those from real surnames). There are no cardholder names, addresses or account numbers in the schema.
- **PII scan.** `scripts/scan_data.py` checks `data/` and `docs/` for Luhn-valid card numbers, emails, US phone numbers and US SSNs. Result at v0.2-data: clean, no findings. It runs in CI on every pull request and blocks the merge on a finding.
- **Not covered.** The scanner does not find names or street addresses. That needs NLP tools such as Presidio (Phase 8).

## Checks in CI

`scripts/validate_data.py` runs on every pull request, with no network and no database. It checks the schema, labels and alt codes, held-out share per code (20% to 30%), ambiguous share (10% to 20%), every code in both splits, unique case ids, and that `generate_disputes(200, 42)` reproduces both files byte for byte. A hand edit fails CI even when the edited row is valid.

## Intended use

- Developing and comparing prompts and models on the dev split.
- Checking whether results carry over, on the held-out split.
- Testing retrieval and citation against the rules corpus (Phase 3).
- Teaching and demonstrating LLMOps practice.

## Not intended for

- Measuring how a model would perform on real disputes. These numbers are an upper bound on clean, templated claims.
- Training or fine-tuning a model for production use.
- Any statement about real card network rules, time limits or reason code definitions.
- Tuning prompts on the held-out split. Once it has been used for tuning, it no longer measures what it is meant to.
