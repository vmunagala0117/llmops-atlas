"""Find card numbers and personal identifiers in text (spec 2.3).

Detects card numbers (13 to 19 digits, optional spaces or dashes, Luhn valid),
email addresses, US phone numbers and US SSNs. Names and addresses need NLP
tools and are out of scope for now.

Findings carry a masked value only, so a report never repeats the full number.
"""

import re
from pathlib import Path

# Digits with optional single spaces or dashes between them, not touching other digits.
_CARD = re.compile(r"(?<!\d)\d(?:[ -]?\d){12,18}(?!\d)")
_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}\b")
# Separators or brackets are required, so a bare 10-digit id is not a phone number.
_PHONE = re.compile(
    r"(?<![\d-])(?:\+1[ .-]?)?(?:\([2-9]\d{2}\) ?|[2-9]\d{2}[ .-])[2-9]\d{2}[ .-]\d{4}(?![\d-])"
)
# Dashes required; skips ranges that are never issued (000, 666, 9xx, 00 group, 0000 serial).
_SSN = re.compile(r"(?<![\d-])(?!000|666|9\d\d)\d{3}-(?!00)\d{2}-(?!0000)\d{4}(?![\d-])")


def luhn_valid(digits: str) -> bool:
    """Return True if ``digits`` (digits only) passes the Luhn checksum."""
    if not digits.isdigit():
        return False
    total = 0
    for i, ch in enumerate(reversed(digits)):
        n = int(ch)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


def _digits(value: str) -> str:
    return re.sub(r"\D", "", value)


def _normalise(kind: str, value: str) -> str:
    if kind == "email":
        return value.lower()
    digits = _digits(value)
    if kind == "phone" and len(digits) == 11:
        return digits[1:]  # +1 country code
    return digits


def _mask(kind: str, value: str) -> str:
    if kind == "card":
        digits = _digits(value)
        return digits[:6] + "*" * (len(digits) - 10) + digits[-4:]
    return f"[{kind}]"


def find_pii(text: str, allow=()) -> list[dict]:
    """Return findings as ``{"type", "masked", "start"}``, sorted by start.

    ``allow`` holds deliberate test values (see ``load_allowlist``). The data
    scan never passes it.
    """
    allowed = {_normalise(kind, v) for v in allow for kind in ("card", "email", "phone")}
    spans: list[tuple[int, int]] = []
    findings = []

    def add(kind, match):
        start, end = match.span()
        if any(start < e and s < end for s, e in spans):
            return  # already reported as a card, for example
        spans.append((start, end))
        if _normalise(kind, match.group()) not in allowed:
            findings.append({"type": kind, "masked": _mask(kind, match.group()), "start": start})

    for match in _CARD.finditer(text):
        if luhn_valid(_digits(match.group())):
            add("card", match)
    for kind, pattern in (("email", _EMAIL), ("ssn", _SSN), ("phone", _PHONE)):
        for match in pattern.finditer(text):
            add(kind, match)
    return sorted(findings, key=lambda f: f["start"])


def load_allowlist(path: str | Path) -> set[str]:
    """Read one value per line; blank lines and ``#`` comments are skipped. For tests only."""
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    return {line.strip() for line in lines if line.strip() and not line.lstrip().startswith("#")}
