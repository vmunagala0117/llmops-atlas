"""Write the synthetic dispute dataset (spec 2.1). Needs no .env and no network.

Run from the repo root: python scripts/make_dataset.py
"""

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from atlas.prompts import REASON_CODES  # noqa: E402
from atlas.synth import generate_disputes  # noqa: E402

N, SEED = 200, 42
OUT = ROOT / "data" / "synthetic"
FILES = {"dev": "disputes_dev.jsonl", "held_out": "disputes_heldout.jsonl"}


def render_files(cases: list[dict]) -> dict[str, str]:
    """File name to exact file text. Shared with validate_data.py, which compares bytes."""
    texts = {}
    for split, name in FILES.items():
        lines = [json.dumps(c) for c in cases if c["split"] == split]
        texts[name] = "\n".join(lines) + "\n"
    return texts


def main() -> None:
    cases = generate_disputes(N, SEED)
    OUT.mkdir(parents=True, exist_ok=True)
    for name, text in render_files(cases).items():
        (OUT / name).write_text(text)

    counts = Counter((c["label_reason_code"], c["split"]) for c in cases)
    print(f"{'code':<6}{'dev':>5}{'held_out':>10}")
    for code in REASON_CODES:
        print(f"{code:<6}{counts[code, 'dev']:>5}{counts[code, 'held_out']:>10}")
    ambiguous = sum(c["difficulty"] == "ambiguous" for c in cases)
    print(f"total {len(cases)}, ambiguous {ambiguous} ({ambiguous / len(cases):.0%})")
    print("wrote", ", ".join(str((OUT / n).relative_to(ROOT)) for n in FILES.values()))


if __name__ == "__main__":
    main()
