"""Run prompt and model variants over labelled cases and score them."""

import json

import pandas as pd

from atlas.llm import call_model
from atlas.prompts import render


def parse_response(text: str | None) -> dict | None:
    """Extract the JSON answer from a model reply. Returns None if it is not usable."""
    if not text:
        return None
    start, end = text.find("{"), text.rfind("}")  # also skips ``` fences and stray prose
    if start == -1 or end <= start:
        return None
    try:
        obj = json.loads(text[start : end + 1])
    except ValueError:
        return None
    if not isinstance(obj, dict) or "reason_code" not in obj:
        return None
    obj["reason_code"] = str(obj["reason_code"]).strip()
    return obj


def variant_name(variant: dict) -> str:
    if variant.get("name"):
        return variant["name"]
    effort = variant.get("params", {}).get("reasoning_effort", "default")
    return f"{variant['prompt_id']} effort={effort}"


def run_experiment(variants: list[dict], cases: list[dict]) -> pd.DataFrame:
    """One row per (variant, case). Each variant is {prompt_id, model, params, name?}."""
    rows = []
    for variant in variants:
        name = variant_name(variant)
        for case in cases:
            messages = render(variant["prompt_id"], case)
            result = call_model(variant["model"], messages, **variant.get("params", {}))
            parsed = parse_response(result["text"])
            predicted = parsed["reason_code"] if parsed else None
            rows.append(
                {
                    "variant": name,
                    "prompt_id": variant["prompt_id"],
                    "case_id": case["case_id"],
                    "label": case["label_reason_code"],
                    "predicted": predicted,
                    "correct": predicted == case["label_reason_code"],
                    "valid_json": parsed is not None,
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
