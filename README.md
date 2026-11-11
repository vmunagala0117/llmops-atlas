# Atlas

An enterprise LLMOps reference platform for a payments company, built in public as a learning project.
The first app is a **Dispute Resolution Copilot** that reads a cardholder's dispute and suggests the Visa reason code an analyst would file it under.

> **All data in this repository is synthetic.** Merchants, amounts and claims are invented. There are no real people, card numbers or transactions anywhere in the code, data or docs.

## The problem

Dispute analysts read free-text claims ("I was charged twice", "it never arrived", "I cancelled") and map each one to a card network reason code. Getting the code wrong delays the case or loses it. An LLM can do a first pass, but only if we can show it is accurate, cheap enough and fast enough, and keep showing it as prompts and models change. That evidence loop is what Atlas is about.

## What is built so far (Phase 1)

- **One model-call path** (`src/atlas/llm.py`): every call goes through `call_model()`, which wraps LiteLLM so the model is a config value, measures latency on the client, records tokens (including hidden reasoning tokens) and cost, and returns errors as data instead of crashing a batch run.
- **Versioned prompts** (`src/atlas/prompts.py`): `dispute_triage@v1` (zero-shot) and `@v2` (decision rules plus one example). Released versions are frozen.
- **Synthetic dataset** (`data/samples/disputes_v1.jsonl`): 12 labelled disputes across eight Visa reason codes, including two deliberately ambiguous cases.
- **Scorecard** (`src/atlas/scorecard.py`, `notebooks/01_baseline_scorecard.ipynb`): compares prompt versions and reasoning effort settings on accuracy, valid JSON rate, error rate, p50/p95 latency, reasoning tokens and cost per 1,000 requests.
- **CI** (`.github/workflows/ci.yml`): lint, tests and the notebook run on every pull request in mock mode, with no network and no secrets.

See [docs/roadmap.md](docs/roadmap.md) for what comes next and [docs/phases/](docs/phases/) for the build journal.

## Skills shown

- Provider-agnostic LLM integration with LiteLLM
- Prompt versioning and controlled experiments
- Evaluation design: labelled data, accuracy, output validity, latency percentiles, unit cost
- Cost and latency trade-offs of reasoning models (reasoning effort as an experiment variable)
- Offline, deterministic testing of LLM code with a mock mode
- CI for ML-adjacent code, including executing notebooks

## Quick start

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt

ATLAS_MOCK=1 pytest -q     # offline tests
ruff check .               # lint
```

To run the scorecard against a real model, create a `.env` file (git-ignored) with `ATLAS_API_BASE`, `ATLAS_API_KEY` and `ATLAS_MODELS` (a LiteLLM model name), then open `notebooks/01_baseline_scorecard.ipynb` in `jupyter lab`. Without credentials, set `ATLAS_MOCK=1` and `ATLAS_MODELS=openai/atlas-ci-mock` to run it offline.

## Repository layout

```
src/atlas/        reusable code imported by notebooks
notebooks/        one notebook per phase
data/samples/     small synthetic datasets
results/          scorecard CSVs from live runs
tests/            offline pytest suite
docs/             roadmap, lifecycle, phase journals
```
