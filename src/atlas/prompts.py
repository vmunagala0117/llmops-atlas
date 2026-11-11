"""Versioned prompts for dispute triage.

Prompt ids follow ``task@vN``. A version is released once it is merged to main.
A released version is frozen: never edit its text. To change a prompt, add a new
version (for example ``dispute_triage@v3``) so older scorecards stay reproducible.
"""

REASON_CODES = {
    "10.4": "Other Fraud: Card-Absent Environment",
    "12.5": "Incorrect Amount",
    "12.6": "Duplicate Processing or Paid by Other Means",
    "13.1": "Merchandise or Services Not Received",
    "13.2": "Cancelled Recurring Transaction",
    "13.3": "Not as Described or Defective Merchandise or Services",
    "13.6": "Credit Not Processed",
    "13.7": "Cancelled Merchandise or Services",
}

_CODE_LIST = "\n".join(f"- {code}: {title}" for code, title in REASON_CODES.items())

_OUTPUT_FORMAT = """Reply with only a JSON object, no other text, in this shape:
{"reason_code": "<one code from the list>", "confidence": <number from 0 to 1>,
 "summary": "<one sentence>", "missing_evidence": ["<evidence an analyst should request>"]}"""

_V1_SYSTEM = f"""You are a card dispute analyst at a payments company.
Classify the cardholder's dispute into exactly one Visa reason code from this list:
{_CODE_LIST}

{_OUTPUT_FORMAT}"""

_V2_SYSTEM = f"""You are a card dispute analyst at a payments company.
Classify the cardholder's dispute into exactly one Visa reason code from this list:
{_CODE_LIST}

Decision rules:
1. Cardholder says they did not make or authorise the purchase: 10.4.
2. Cardholder made the purchase but the amount is wrong: 12.5.
3. Same purchase charged twice, or already paid another way (cash, other card): 12.6.
4. Goods or services never arrived and no refund was confirmed in writing: 13.1.
5. An ongoing subscription or membership was cancelled but billing continued: 13.2.
6. Goods arrived damaged, defective or different from the description: 13.3.
7. Merchant confirmed a refund or credit in writing, but it never arrived: 13.6.
8. A one-off order or booking was cancelled under the merchant's policy but still charged: 13.7.
If two rules seem to fit, choose the code whose conditions the claim actually shows,
not the one it only hints at, and list in missing_evidence what would settle it.

Example
Claim: "I ordered a wool coat but received a thin polyester one. The listing clearly
said 100 percent wool."
Answer: {{"reason_code": "13.3", "confidence": 0.9,
 "summary": "Item received differs materially from the listing.",
 "missing_evidence": ["product listing", "photos of item received"]}}

{_OUTPUT_FORMAT}"""

PROMPTS = {
    "dispute_triage@v1": _V1_SYSTEM,  # released: zero-shot
    "dispute_triage@v2": _V2_SYSTEM,  # released: decision rules plus one example
}


def _case_text(case: dict) -> str:
    # Only the facts an analyst sees. Never include the label.
    return "\n".join(
        [
            "Dispute case:",
            f"Channel: {case['channel']}",
            f"Amount (USD): {case['amount_usd']}",
            f"Merchant: {case['merchant']} (MCC {case['mcc']})",
            f"Cardholder claim: {case['cardholder_claim']}",
        ]
    )


def render(prompt_id: str, case: dict) -> list[dict]:
    """Return chat messages for one case. Raises KeyError for an unknown prompt id."""
    return [
        {"role": "system", "content": PROMPTS[prompt_id]},
        {"role": "user", "content": _case_text(case)},
    ]
