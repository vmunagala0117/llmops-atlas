# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Atlas is an enterprise LLMOps reference platform for a payments company, built as a learning project.
Its first app, the Dispute Resolution Copilot, classifies card disputes into Visa reason codes; all data is synthetic.

## Layout

- `src/atlas/`: reusable code. `llm.py` (the model-call path), `prompts.py` (versioned prompts, `render()`), `scorecard.py` (experiments and metrics)
- `notebooks/`: one notebook per phase; thin, adds `src/` to `sys.path` and imports from `atlas`
- `data/samples/`: small synthetic dispute samples (JSONL)
- `results/`: scorecard CSVs; `*_live.csv` is kept, `*_mock.csv` is git-ignored
- `tests/`: offline pytest suite; `conftest.py` forces mock mode for every test
- `scripts/`: manual scripts that need a real `.env` (not run in CI)
- `docs/`: roadmap, lifecycle, phase journals
- `.github/workflows/ci.yml`: ruff, pytest and the notebook, all with `ATLAS_MOCK=1`

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

## Working with me

I'm learning. Briefly explain the reasoning behind each change, and keep changes small enough to review in one sitting.
