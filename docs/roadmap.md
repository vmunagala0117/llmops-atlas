# Roadmap

Each phase ships as one pull request and ends with a tag. Phases not listed here are not planned in detail yet.

| Phase | Status | Tag | Scope |
| --- | --- | --- | --- |
| 1. Baseline copilot and model scorecard | Done | `v0.1-baseline` | One model-call path, versioned prompts, 12-case sample, scorecard, CI in mock mode |
| 2. Data | Done | `v0.2-data`, `v0.2.1-data` | Synthetic generator with held-out split, rules corpus, PII scanner, pgvector ingestion, data card, data checks in CI, walkthrough notebook |
| 3. Retrieval with citations | Next | | Retrieve rule sections by meaning and cite them as `code@version` |
| 6. Evaluation gate | Planned | | Golden set and an accuracy gate in CI |
| 8. PII beyond patterns | Planned | | Names and addresses with NLP tools such as Presidio |

## Carried into Phase 3

- Retrieval must filter to the current version of each rules file. Old versions stay in the table so old citations resolve.
- The intro paragraph of `choosing-between-codes.md` is not ingested, because it sits before the first `##` section.
- No vector index yet. 38 rows need none.
- `render()` prints `amount_usd` as a raw float. Fixing it needs new prompt versions.
