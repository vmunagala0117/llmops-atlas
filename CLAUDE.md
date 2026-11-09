# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Atlas is an enterprise LLMOps reference platform for a payments company, built as a learning project.
Its first app, the Dispute Resolution Copilot, classifies card disputes into Visa reason codes; all data is synthetic.

## Layout (planned: create directories as phases need them)

- `notebooks/`: one notebook per phase; thin, imports logic from `src/atlas/`
- `src/atlas/`: reusable code (LLM client, prompts, classifiers, evals)
- `data/samples/`: small synthetic dispute samples
- `tests/`: pytest tests for `src/atlas/`
- `docs/`: design notes and phase write-ups

## Commands

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
pytest -q                                  # all tests
pytest -q tests/test_x.py::test_name       # single test
ruff check .                               # lint
```

## Rules

- **One model-call path.** Every LLM call goes through a single function in `src/atlas/` that wraps LiteLLM.
  Never call `litellm` or a provider SDK directly from notebooks or other modules.
- **Versioned prompts.** Prompts are identified as `task@vN` (e.g. `classify_dispute@v1`).
  A released version is never edited: changes mean a new version (`@v2`).
- **Secrets.** Keys live in `.env` (loaded via python-dotenv, git-ignored). Never commit `.env` or secrets.
- **Synthetic data only.** No real personal data or card numbers (PANs) anywhere: data, tests, prompts, or notebooks.
- **Offline tests.** Tests never call real models or need network access. Use `ATLAS_MOCK=1` for an offline test double.
- **No hardcoded model names.** Model and deployment names come from environment variables (for example `ATLAS_MODELS`), never hardcoded.
- **Small changes.** One phase per pull request; keep diffs small.
- **Verify before finishing.** Before saying a change is done, run `pytest -q` and `ruff check .`.

## Documentation

- The repo is the portfolio: write for recruiters (README), engineers (docs/architecture, docs/adr) and future revision (docs/phases).
- During a phase, add short notes to `docs/phases/phase-NN-<name>.md` as work lands.
- At each milestone tag, update README status, `docs/roadmap.md`, `CHANGELOG.md` and the phase journal.
- Never include tenant names, subscription IDs, real endpoints or keys in any document.
- Plain language, no en dashes.

## Working with me

I'm learning. Briefly explain the reasoning behind each change, and keep changes small enough to review in one sitting.
