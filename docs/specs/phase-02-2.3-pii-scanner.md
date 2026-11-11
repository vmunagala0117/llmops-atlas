# Spec 2.3: PII and card number scanner

## Why
Data must pass a privacy check before use. A real card number or personal identifier in the repo is a compliance incident, so the check is automated and blocking.

## Requirements
1. `src/atlas/pii.py`:
   - `luhn_valid(digits: str) -> bool`
   - `find_pii(text: str) -> list[dict]` detecting: card numbers (13 to 19 digits, optional spaces or dashes, must pass Luhn), email addresses, US phone numbers, US SSNs. Each finding: type, masked value, start position.
   - Masking: card numbers show first 6 and last 4 only; others fully masked except type.
2. `scripts/scan_data.py`: scans `data/` and `docs/` recursively (jsonl, md, csv, txt); prints findings as file:line, type, masked value; exits 1 if any finding, 0 if clean.
3. An allowlist file `config/pii_allowlist.txt` for deliberate test values, used only by tests; the data scan never allows them.

## Acceptance criteria
- Tests: Luhn valid and invalid; spaced and dashed card numbers found; amounts, dates, case ids, reason codes and MCCs not flagged; masked output never contains the full number.
- Running the scan on the current repo exits 0.
- A test proves that inserting a Luhn-valid number into a temporary data file makes the scan exit 1.

## Out of scope
Names and addresses (need NLP tools such as Presidio; noted for Phase 8), running the scan in CI (Step 2.5).

## Decisions

1. **The allowlist has a job of its own.** A test scans `tests/` with the allowlist and fails on any value not listed, so every deliberate fake value is written down in one place. Another test checks that every entry is something the scanner flags, so the list cannot fill up with typos. A test that needs an unlisted number builds it at runtime instead of writing it out.
2. **Test card numbers are the networks' published test numbers**, which pass Luhn but are not real cards. They live only in `tests/` and `config/`, which the data scan does not read, and never in `docs/`.
3. **Phone numbers need separators or brackets** and an area code starting 2 to 9, so a bare 10-digit id is not flagged. A leading +1 is ignored when comparing with the allowlist.
4. **SSNs need dashes**, and ranges that are never issued (000, 666, 9xx, a 00 group, a 0000 serial) are skipped. Dates have a different shape and never match.
5. **Masking:** cards show the first 6 and last 4 digits; other types show only `[email]`, `[phone]` or `[ssn]`.
6. **Overlaps are reported once.** Cards are matched first, and a later match that overlaps an earlier one is dropped.
7. **`scripts/scan_data.py` accepts paths**, defaulting to `data/` and `docs/`, so tests can scan a temporary folder. It never loads the allowlist.
