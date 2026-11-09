import os

import pytest

# LiteLLM downloads its model price list on import unless told to use the bundled copy.
# Set this before atlas.llm (and so litellm) is imported, so tests never touch the network.
os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")


@pytest.fixture(autouse=True)
def mock_mode(monkeypatch):
    """Every test runs in mock mode, so no test can reach a real model."""
    monkeypatch.setenv("ATLAS_MOCK", "1")
