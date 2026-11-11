# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Atlas is an enterprise LLMOps reference platform for a payments company, built as a learning project.
Its first app, the Dispute Resolution Copilot, classifies card disputes into Visa reason codes; all data is synthetic.

## Layout

- `src/atlas/`: reusable code. `llm.py` (the model-call path), `prompts.py` (versioned prompts, `render()`), `scorecard.py` (experiments and metrics), `synth.py` (synthetic dispute generator), `corpus.py` (rules loader), `pii.py` (card number and PII detection), `chunking.py` (rules into section chunks), `store.py` (Postgres and pgvector store)
- `notebooks/`: one notebook per phase; thin, adds `src/` to `sys.path` and imports from `atlas`
- `data/samples/`: small synthetic dispute samples (JSONL)
- `data/synthetic/`: generated datasets (`disputes_dev.jsonl`, `disputes_heldout.jsonl`); rebuild with `python scripts/make_dataset.py`, never edit by hand
- `data/rules/`: illustrative rules corpus, one markdown file per reason code with YAML front matter; bump `version` when editing a released file
- `results/`: scorecard CSVs; `*_live.csv` is kept, `*_mock.csv` is git-ignored
- `tests/`: offline pytest suite; `conftest.py` forces mock mode for every test
- `scripts/`: manual scripts. Most need a real `.env`; `make_dataset.py`, `scan_data.py` (PII scan of `data/` and `docs/`) and `validate_data.py` (schema, shares, reproducible from seed 42) do not, and the last two run in CI and exit 1 on a problem. `ingest_rules.py` needs `ATLAS_DB_URL` and prints the server it connected to first
- `config/`: `pii_allowlist.txt`, the deliberate fake values in `tests/`; used by tests only, never by the data scan
- `docs/`: roadmap, data card, specs, phase journals, case studies (`docs/case_studies/`)
- `docker-compose.yml`: optional Postgres with pgvector on host port 5433; the primary store is a native Postgres on 5432
- `.github/workflows/ci.yml`: ruff, pytest, PII scan, data validation and the notebook, all with `ATLAS_MOCK=1`, no network and no database

## Commands

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
pytest -q                                  # all tests
pytest -q tests/test_x.py::test_name       # single test
ruff check .                               # lint
ATLAS_MOCK=1 ATLAS_MODELS=openai/atlas-ci-mock \
  jupyter nbconvert --to notebook --execute notebooks/01_baseline_scorecard.ipynb --output-dir /tmp
```

Mock mode needs a provider-prefixed model name (`openai/...`); bare names fail in LiteLLM.

## Rules

- **One model-call path.** Every LLM call goes through `call_model()` in `src/atlas/llm.py`, which wraps LiteLLM.
  Never call `litellm` or a provider SDK directly from notebooks or other modules.
- **Versioned prompts.** Prompts are identified as `task@vN` (e.g. `dispute_triage@v1`).
  A released version is never edited: changes mean a new version (`@v2`).
- **Secrets.** Keys live in `.env` (loaded via python-dotenv, git-ignored). Never commit `.env` or secrets.
- **Synthetic data only.** No real personal data or card numbers (PANs) anywhere: data, tests, prompts, or notebooks.
- **Offline tests.** Tests never call real models or need network access. Use `ATLAS_MOCK=1` for an offline test double.
- **No hardcoded model names.** Model and deployment names come from environment variables (for example `ATLAS_MODELS`), never hardcoded.
- **Small changes.** One phase per pull request; keep diffs small.
- **Verify before finishing.** Before saying a change is done, run `pytest -q` and `ruff check .`.

## Documentation

- The repo is the portfolio: write for reviewers (README), engineers (docs/architecture, docs/adr) and future revision (docs/phases).
- During a phase, add short notes to `docs/phases/phase-NN-<name>.md` as work lands.
- At each milestone tag, update README status, `docs/roadmap.md`, `CHANGELOG.md` and the phase journal.
- Never include tenant names, subscription IDs, real endpoints or keys in any document.
- Plain language, no en dashes.
- When a non-trivial problem is found and fixed, add a case study in `docs/case_studies/` (context, symptom, investigation, root cause, fix steps, result, lessons, interview version) and list it in the index.

## Working with me

I'm learning. Briefly explain the reasoning behind each change, and keep changes small enough to review in one sitting.
