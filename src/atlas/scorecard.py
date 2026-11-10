"""Run prompt and model variants over labelled cases and score them."""

import json
import os
import time
from pathlib import Path

import pandas as pd

from atlas.llm import call_model
from atlas.parsing import parse_reply
from atlas.prompts import render


def load_cases(path: str | Path) -> list[dict]:
    """Read labelled cases from a JSONL file, one object per line."""
    lines = Path(path).read_text().splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def predicted_code(text: str | None) -> str | None:
    """The reason code in a reply, or None if the reply is not a usable answer."""
    obj = parse_reply(text)
    if obj is None or "reason_code" not in obj:
        return None
    return str(obj["reason_code"]).strip()


def _call_delay_s() -> float:
    # Optional pause between calls, for a low token-per-minute quota. Default: none.
    return float(os.environ.get("ATLAS_CALL_DELAY_S", "0"))


def variant_name(variant: dict) -> str:
    if variant.get("name"):
        return variant["name"]
    effort = variant.get("params", {}).get("reasoning_effort", "default")
    return f"{variant['prompt_id']} effort={effort}"


def run_experiment(variants: list[dict], cases: list[dict]) -> pd.DataFrame:
    """One row per (variant, case), calls made one after another.

    Each variant is {name, prompt_id, model, params}. If name is missing it is built
    from the prompt id and reasoning effort. Names must be unique.
    """
    names = [variant_name(v) for v in variants]
    duplicates = sorted({n for n in names if names.count(n) > 1})
    if duplicates:
        # summarize() groups by name, so duplicates would be averaged into one row.
        raise ValueError(f"variant names must be unique, got duplicates: {duplicates}")

    delay_s = _call_delay_s()
    rows = []
    for variant, name in zip(variants, names, strict=True):
        for case in cases:
            if rows and delay_s:
                time.sleep(delay_s)
            messages = render(variant["prompt_id"], case)
            result = call_model(variant["model"], messages, **variant.get("params", {}))
            predicted = predicted_code(result["text"])
            rows.append(
                {
                    "variant": name,
                    "prompt_id": variant["prompt_id"],
                    "case_id": case["case_id"],
                    "label": case["label_reason_code"],
                    "predicted": predicted,
                    "correct": predicted == case["label_reason_code"],
                    "valid_json": predicted is not None,  # JSON with a reason_code
                    "error": result["error"],
                    "prompt_tokens": result["prompt_tokens"],
                    "completion_tokens": result["completion_tokens"],
                    "reasoning_tokens": result["reasoning_tokens"],
                    "cost_usd": result["cost_usd"],
                    "latency_ms": result["latency_ms"],
                }
            )
    return pd.DataFrame(rows)


def summarize(df: pd.DataFrame) -> pd.DataFrame:
    """Per-variant scorecard, in the order the variants were run."""
    grouped = df.groupby("variant", sort=False)
    return pd.DataFrame(
        {
            "n": grouped.size(),
            "accuracy": grouped["correct"].mean(),
            "valid_json_rate": grouped["valid_json"].mean(),
            "error_rate": grouped["error"].apply(lambda s: s.notna().mean()),
            "p50_latency_ms": grouped["latency_ms"].quantile(0.5),
            "p95_latency_ms": grouped["latency_ms"].quantile(0.95),
            "avg_reasoning_tokens": grouped["reasoning_tokens"].mean(),
            "cost_per_1k_usd": grouped["cost_usd"].mean() * 1000,
        }
    )
