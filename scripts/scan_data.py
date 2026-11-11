"""Scan data/ and docs/ for card numbers and personal identifiers (spec 2.3).

Usage: python scripts/scan_data.py [PATH ...]

Prints one line per finding (file:line, type, masked value) and exits 1 if
anything is found, 0 if clean. The allowlist is never used here: it exists only
for deliberate test values in tests/. Needs no .env.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from atlas.pii import find_pii  # noqa: E402

SUFFIXES = {".jsonl", ".md", ".csv", ".txt"}
DEFAULT_PATHS = [ROOT / "data", ROOT / "docs"]


def files_under(paths):
    for path in paths:
        if path.is_file():
            yield path
        else:
            yield from sorted(p for p in path.rglob("*") if p.is_file() and p.suffix in SUFFIXES)


def scan(paths) -> int:
    count = 0
    for file in files_under(paths):
        text = file.read_text(encoding="utf-8", errors="replace")
        for line_no, line in enumerate(text.splitlines(), start=1):
            for finding in find_pii(line):
                count += 1
                print(f"{file}:{line_no}: {finding['type']} {finding['masked']}")
    return count


def main(argv) -> int:
    paths = [Path(a) for a in argv] or DEFAULT_PATHS
    count = scan(paths)
    print(f"{count} finding(s)" if count else "clean: no findings")
    return 1 if count else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
