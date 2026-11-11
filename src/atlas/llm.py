"""The single model-call path for Atlas. Every LLM call goes through call_model()."""

import logging
import math
import os
import time

import litellm
from dotenv import load_dotenv

load_dotenv()  # never overrides variables that are already set

logger = logging.getLogger(__name__)

# A valid answer in the prompt's output format, so mock runs exercise parsing and scoring.
MOCK_REPLY = (
    '{"reason_code": "13.1", "confidence": 0.5, '
    '"summary": "Mock reply for offline runs.", "missing_evidence": []}'
)
DEFAULT_TIMEOUT_S = 60
DEFAULT_NUM_RETRIES = 2
MAX_ERROR_CHARS = 200


def _result(model: str, **fields) -> dict:
    """Build a result dict that always has every key."""
    base = {
        "model": model,
        "text": "",
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "reasoning_tokens": 0,
        "cost_usd": 0.0,
        "latency_ms": 0,
        "error": None,
    }
    base.update(fields)
    return base


def _short_error(exc: Exception) -> str:
    lines = str(exc).strip().splitlines()
    first_line = lines[0] if lines else ""
    return f"{type(exc).__name__}: {first_line}"[:MAX_ERROR_CHARS]


def _cost(response) -> float:
    """Estimated cost in USD, or NaN when it is unknown (so it never reads as free)."""
    try:
        cost = litellm.completion_cost(completion_response=response)
    except Exception:
        return math.nan  # unknown model price or unexpected response shape
    return math.nan if cost is None else float(cost)


def call_model(model: str, messages: list[dict], **params) -> dict:
    """Call a model through LiteLLM and return a flat result dict. Never raises."""
    mock = os.environ.get("ATLAS_MOCK") == "1"
    if mock:
        params["mock_response"] = MOCK_REPLY
    params.setdefault("timeout", DEFAULT_TIMEOUT_S)
    params.setdefault("num_retries", DEFAULT_NUM_RETRIES)

    start = time.perf_counter()
    try:
        response = litellm.completion(
            model=model,
            messages=messages,
            api_base=os.environ.get("ATLAS_API_BASE"),
            api_key=os.environ.get("ATLAS_API_KEY"),
            drop_params=True,
            **params,
        )
        latency_ms = round((time.perf_counter() - start) * 1000)

        usage = getattr(response, "usage", None)
        details = getattr(usage, "completion_tokens_details", None)
        return _result(
            model,
            text=response.choices[0].message.content or "",
            prompt_tokens=getattr(usage, "prompt_tokens", None) or 0,
            completion_tokens=getattr(usage, "completion_tokens", None) or 0,
            reasoning_tokens=getattr(details, "reasoning_tokens", None) or 0,
            cost_usd=0.0 if mock else _cost(response),  # never price fake tokens
            latency_ms=latency_ms,
        )
    except Exception as exc:
        # Broad on purpose so a batch run keeps going, but logged so real bugs stay visible.
        latency_ms = round((time.perf_counter() - start) * 1000)
        logger.warning("call_model failed for model %s", model, exc_info=True)
        return _result(model, latency_ms=latency_ms, error=_short_error(exc))
