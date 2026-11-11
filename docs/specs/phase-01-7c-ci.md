# Spec 7c CI: GitHub Actions pipeline

## Why
Nothing reaches main unless it passes. This is the build-and-test stage of the LLMOps lifecycle; Phase 6 adds the evaluation gate here.

## Requirements
- `.github/workflows/ci.yml`, triggered on pull requests and on push to main.
- Steps: checkout, Python 3.12 with pip cache, install requirements, `ruff check .`, `pytest -q`, execute the notebook with ATLAS_MOCK=1.
- No secrets and no network calls to models. Read-only permissions.

## Acceptance criteria
- The workflow passes on the pull request.