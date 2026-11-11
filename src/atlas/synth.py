"""Reproducible synthetic dispute cases.

``generate_disputes(n, seed)`` builds labelled cases from claim templates. The same
seed always gives the same cases (with the pinned Faker version in requirements.txt).

Held-out cases are built only from HELD_OUT templates. When writing or tuning
prompts, do not read HELD_OUT_TEMPLATES or the held-out data file.
"""

import datetime as dt
import random
from dataclasses import dataclass

from faker import Faker

from atlas.prompts import REASON_CODES

AMBIGUOUS_SHARE = 0.15
HELD_OUT_SHARE = 0.25
DATE_START = dt.date(2026, 1, 1)  # fixed window: never relative to today
DATE_END = dt.date(2026, 6, 30)
TYPO_RATE = 0.25
MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]  # fmt: skip
# Own list instead of strftime("%B"), which depends on the machine's locale.


@dataclass(frozen=True)
class Category:
    mcc: str
    suffix: str  # merchant name ending, for example "Electronics"
    items: tuple[str, ...]
    min_usd: int
    max_usd: int


CATEGORIES = {
    "electronics": Category(
        "5732", "Electronics", ("laptop", "tablet", "smart speaker", "games console"), 80, 1500
    ),  # noqa: E501
    "apparel": Category(
        "5651", "Apparel", ("jacket", "winter coat", "pair of boots", "dress"), 40, 300
    ),  # noqa: E501
    "furniture": Category(
        "5712", "Home", ("sofa", "dining table", "bookcase", "desk chair"), 150, 2000
    ),  # noqa: E501
    "appliances": Category(
        "5722", "Appliances", ("blender", "coffee machine", "microwave", "vacuum cleaner"), 40, 400
    ),  # noqa: E501
    "restaurant": Category("5812", "Bistro", ("dinner",), 20, 180),
    "fuel": Category("5541", "Fuel", ("fuel",), 30, 110),
    "streaming": Category("4899", "Stream", ("plan",), 8, 25),
    "fitness": Category("7997", "Fitness Club", ("membership",), 20, 90),
    "meal_kits": Category("5499", "Meal Kits", ("meal kit box",), 40, 120),
    "games": Category("5816", "Games", ("game credits",), 5, 100),
    "moving": Category("4214", "Movers", ("move",), 150, 900),
    "hotel": Category("7011", "Hotel", ("room",), 90, 600),
    "florist": Category("5992", "Florist", ("flower order",), 30, 150),
}

# Invented first parts, so names are fictional by construction (no real surnames).
MERCHANT_PREFIXES = [
    "Brovane", "Corvella", "Dunmarsh", "Fernhollow", "Halvane", "Kindlebay",
    "Marrowfen", "Ostrell", "Plinthwood", "Quillmark", "Sablecrest", "Tarnwick",
    "Velmora", "Voltway", "Wrenlow", "Zentrik",
]  # fmt: skip

OPENERS = {
    "neutral": [""],
    "frustrated": ["I am really frustrated. ", "This is the second time I am asking. "],
    "polite": ["Hello, ", "Hi, I need help with a charge. "],
}
CLOSERS = {
    "neutral": [""],
    "frustrated": [" This is unacceptable.", " I want my money back."],
    "polite": [" Thank you for your help.", " Thanks in advance."],
}
# Extra details that never change the label.
EXTRA_DETAILS = [
    "I noticed it when checking my statement this morning.",
    "I have been a customer for years.",
    "This is the first time I have had to dispute anything.",
]

ONLINE = ("online",)
CARD_ABSENT = ("online", "phone")
RETAIL = ("electronics", "apparel", "furniture", "appliances")


@dataclass(frozen=True)
class Template:
    template_id: str
    label: str
    split: str  # "dev" or "held_out"
    difficulty: str  # "standard" or "ambiguous"
    categories: tuple[str, ...]
    channels: tuple[str, ...]
    text: str
    alt_reason_code: str | None = None
    correct_ratio: tuple[float, float] = (0.4, 0.9)  # 12.5 only: true amount / charged


def _t(tid, label, split, difficulty, categories, channels, text, alt=None, **kw):
    return Template(tid, label, split, difficulty, categories, channels, text, alt, **kw)


DEV_TEMPLATES = [
    # 10.4 Other Fraud: Card-Absent Environment
    _t("10.4-a", "10.4", "dev", "standard", ("electronics", "games"), CARD_ABSENT,
       "I do not recognise a charge of {amount} from {merchant} on {date}. I have never "
       "shopped there and my card has not left my wallet."),
    _t("10.4-b", "10.4", "dev", "standard", ("electronics", "apparel", "games"), CARD_ABSENT,
       "There is a payment of {amount} to {merchant} that I did not make. Nobody else has "
       "access to my card, and I have never heard of this company."),
    _t("10.4-c", "10.4", "dev", "standard", ("games", "electronics"), ONLINE,
       "Several charges from {merchant} appeared on {date}, totalling {amount}. I did not "
       "authorise them and I think my card details were stolen."),
    _t("10.4-amb-a", "10.4", "dev", "ambiguous", ("streaming", "fitness"), ONLINE,
       "{merchant} has been charging me {amount} a month since {date}. I do not remember "
       "ever signing up. I may have looked at a free trial once, but I never created an "
       "account or gave them my card.", alt="13.2"),
    # 12.5 Incorrect Amount
    _t("12.5-a", "12.5", "dev", "standard", ("restaurant",), ("in_store",),
       "My bill at {merchant} on {date} was {correct_amount}, but my statement shows "
       "{amount}. I have the receipt with the correct total."),
    _t("12.5-b", "12.5", "dev", "standard", RETAIL, ("in_store", "online"),
       "I agreed to pay {correct_amount} for the {item}, but {merchant} charged {amount}. "
       "The price was clearly shown before I paid."),
    _t("12.5-c", "12.5", "dev", "standard", ("fuel", "restaurant"), ("in_store",),
       "{merchant} charged {amount} instead of the {correct_amount} on my receipt. I made "
       "one purchase and the amount is simply wrong."),
    _t("12.5-amb-a", "12.5", "dev", "ambiguous", ("restaurant", "fuel"), ("in_store",),
       "I thought {merchant} had charged me twice, but it is one charge of {amount} when "
       "my receipt says {correct_amount}. There is only one transaction on my statement.",
       alt="12.6", correct_ratio=(0.48, 0.52)),
    # 12.6 Duplicate Processing or Paid by Other Means
    _t("12.6-a", "12.6", "dev", "standard", ("fuel", "restaurant"), ("in_store",),
       "I was charged {amount} twice by {merchant} on {date}, a few minutes apart. I only "
       "made one purchase."),
    _t("12.6-b", "12.6", "dev", "standard", RETAIL + ("florist",), ("in_store",),
       "I paid {merchant} for my {item} in cash and have the cash receipt, but they also "
       "charged {amount} to my card."),
    _t("12.6-c", "12.6", "dev", "standard", RETAIL, ONLINE,
       "{merchant} took {amount} from my card on {date} and again on {later_date} for the "
       "same order. There was only ever one order."),
    _t("12.6-amb-a", "12.6", "dev", "ambiguous", RETAIL, ONLINE,
       "{merchant} charged me {amount} on {date} and again {amount} on {later_date}. They "
       "say the second charge corrects the amount, but the amounts are identical and I "
       "made one purchase.", alt="12.5"),
    # 13.1 Merchandise or Services Not Received
    _t("13.1-a", "13.1", "dev", "standard", RETAIL, CARD_ABSENT,
       "I ordered a {item} from {merchant} on {date} for {amount}. Delivery was promised "
       "within a week, but after {weeks} weeks nothing has arrived and they do not reply."),
    _t("13.1-b", "13.1", "dev", "standard", RETAIL, ONLINE,
       "{merchant} took {amount} for a {item} that never arrived. The tracking number they "
       "gave me does not work."),
    _t("13.1-c", "13.1", "dev", "standard", RETAIL, CARD_ABSENT,
       "I paid {amount} on {date} for a {item}. {merchant} keeps saying it is on its way, "
       "but it has been {weeks} weeks and I have received nothing."),
    _t("13.1-amb-a", "13.1", "dev", "ambiguous", RETAIL, ONLINE,
       "Tracking says my {item} from {merchant} was delivered, but it never came. They "
       "said they would refund me once the courier confirms it is lost. That was {days} "
       "days ago, and I have no {item} and no refund.", alt="13.6"),
    # 13.2 Cancelled Recurring Transaction
    _t("13.2-a", "13.2", "dev", "standard", ("streaming", "fitness"), ONLINE,
       "I cancelled my monthly {merchant} {item} on {earlier_date} and have the cancellation "
       "email. They still charged me {amount} on {date}."),
    _t("13.2-b", "13.2", "dev", "standard", ("fitness",), CARD_ABSENT,
       "I ended my {merchant} membership on {earlier_date}, as their terms allow, but they keep "
       "billing me {amount} every month."),
    _t("13.2-c", "13.2", "dev", "standard", ("streaming", "fitness"), ONLINE,
       "{merchant} charged {amount} on {date} for a subscription I cancelled on "
       "{earlier_date}. I have the confirmation number."),
    _t("13.2-amb-a", "13.2", "dev", "ambiguous", ("streaming", "fitness"), ONLINE,
       "I did not recognise a {amount} charge from {merchant} on {date}. Then I "
       "found I had started a free trial and cancelled it on {earlier_date}. They billed me "
       "anyway.", alt="10.4"),
    # 13.3 Not as Described or Defective Merchandise or Services
    _t("13.3-a", "13.3", "dev", "standard", RETAIL, ("online", "in_store"),
       "The {item} from {merchant} arrived broken and does not work. I paid {amount} and "
       "they refuse to take it back."),
    _t("13.3-b", "13.3", "dev", "standard", RETAIL, ONLINE,
       "I bought a {item} described as new, but {merchant} sent a used one with scratches "
       "and missing parts."),
    _t("13.3-c", "13.3", "dev", "standard", RETAIL, ONLINE,
       "The {item} I received from {merchant} is not what the listing described. It is a "
       "much cheaper version, and I paid {amount}."),
    _t("13.3-amb-a", "13.3", "dev", "ambiguous", RETAIL, ONLINE,
       "The box from {merchant} arrived, but instead of the {item} I ordered it held a "
       "cheaper model. So I never got what I paid {amount} for, and they will not "
       "exchange it.", alt="13.1"),
    # 13.6 Credit Not Processed
    _t("13.6-a", "13.6", "dev", "standard", RETAIL, ("online", "in_store"),
       "I returned the {item} to {merchant} and they emailed a refund confirmation for "
       "{amount} on {later_date}. After {days} days the credit has still not reached my card."),
    _t("13.6-b", "13.6", "dev", "standard", RETAIL, ("in_store",),
       "{merchant} gave me a credit slip for {amount} on {later_date} after I returned my "
       "{item}, but the refund never appeared."),
    _t("13.6-c", "13.6", "dev", "standard", RETAIL, ONLINE,
       "My return was accepted by {merchant} on {later_date} and they confirmed in writing that "
       "{amount} would be refunded. Nothing has arrived after {days} days."),
    _t("13.6-amb-a", "13.6", "dev", "ambiguous", RETAIL, ONLINE,
       "My {item} from {merchant} never arrived, so they cancelled the order and emailed "
       "me a refund confirmation for {amount} on {later_date}. The refund has still not reached "
       "my card.", alt="13.1"),
    # 13.7 Cancelled Merchandise or Services
    _t("13.7-a", "13.7", "dev", "standard", ("hotel", "moving"), CARD_ABSENT,
       "I booked with {merchant} and cancelled on {earlier_date}, well within their free "
       "cancellation period. They still charged me {amount}."),
    _t("13.7-b", "13.7", "dev", "standard", ("florist", "furniture"), ONLINE,
       "I cancelled my order with {merchant} on {earlier_date}, before it was dispatched, and they "
       "confirmed the cancellation. I was charged {amount} anyway."),
    _t("13.7-c", "13.7", "dev", "standard", ("moving", "hotel"), ("phone",),
       "{merchant} kept my {amount} deposit even though I cancelled {days} days ahead, and "
       "their policy allows free cancellation up to 48 hours before."),
    _t("13.7-amb-a", "13.7", "dev", "ambiguous", ("meal_kits",), ONLINE,
       "I placed one order for a {item} from {merchant} and cancelled it online before it "
       "shipped. They charged {amount} anyway. Their site calls it a subscription, but I "
       "only ever placed this single order.", alt="13.2"),
]  # fmt: skip

# Used only for held_out cases. Do not read these when writing or tuning prompts.
HELD_OUT_TEMPLATES = [
    _t("10.4-h", "10.4", "held_out", "standard", ("electronics", "apparel"), CARD_ABSENT,
       "My banking app flagged a purchase at {merchant} for {amount} on {date}. It was not "
       "me. I was at work all day and have never given this merchant my details."),
    _t("10.4-amb-h", "10.4", "held_out", "ambiguous", ("streaming", "fitness"), ONLINE,
       "I keep seeing a monthly charge of {amount} from {merchant}. I have never been a "
       "member there and they have no account under my email, so I believe someone else "
       "is using my card.", alt="13.2"),
    _t("12.5-h", "12.5", "held_out", "standard", ("restaurant", "fuel"), ("in_store",),
       "The total I signed for at {merchant} was {correct_amount}. A few days later "
       "{amount} came off my card for the same purchase. Someone keyed in the wrong "
       "figure."),
    _t("12.5-amb-h", "12.5", "held_out", "ambiguous", RETAIL, ("in_store",),
       "My statement shows a single {merchant} payment of {amount}, roughly double the "
       "{correct_amount} on my receipt. It looks like a double charge, but it is one wrong "
       "amount.", alt="12.6", correct_ratio=(0.48, 0.52)),
    _t("12.6-h", "12.6", "held_out", "standard", RETAIL, ONLINE,
       "I paid for the {item} with my other card, and {merchant} confirmed that payment. "
       "They then charged this card {amount} as well for the same purchase."),
    _t("12.6-amb-h", "12.6", "held_out", "ambiguous", RETAIL, ("in_store",),
       "There are two {merchant} charges of {amount} for my {item}. The shop says one is a "
       "price adjustment, but I only bought the item once and both charges are the full "
       "price.", alt="12.5"),
    _t("13.1-h", "13.1", "held_out", "standard", RETAIL, CARD_ABSENT,
       "Still waiting for the {item} I bought from {merchant} on {date}. It is {weeks} "
       "weeks late, the seller has gone quiet, and I have been charged {amount}."),
    _t("13.1-amb-h", "13.1", "held_out", "ambiguous", RETAIL, CARD_ABSENT,
       "The {item} I paid {amount} for never arrived. {merchant} said on the phone that "
       "they might refund me, but nothing is confirmed and they now ignore my messages.",
       alt="13.6"),
    _t("13.2-h", "13.2", "held_out", "standard", ("streaming", "fitness"), ONLINE,
       "My {merchant} subscription should have stopped after I cancelled it on {earlier_date}. "
       "Instead another {amount} renewal went through on {date}."),
    _t("13.2-amb-h", "13.2", "held_out", "ambiguous", ("streaming", "fitness"), ONLINE,
       "At first I thought the {amount} from {merchant} was fraud. It turns out it is a "
       "renewal of a plan I cancelled on {earlier_date}, and I have the cancellation email.",
       alt="10.4"),
    _t("13.3-h", "13.3", "held_out", "standard", RETAIL, ("online", "in_store"),
       "After two days the {item} from {merchant} stopped working completely. It was sold "
       "as brand new for {amount}, and the seller will not repair or replace it."),
    _t("13.3-amb-h", "13.3", "held_out", "ambiguous", RETAIL, ONLINE,
       "{merchant} delivered a {item}, but it is missing its main parts and cannot be "
       "used. They say the order was delivered, so they owe me nothing.", alt="13.1"),
    _t("13.6-h", "13.6", "held_out", "standard", RETAIL, ("in_store", "online"),
       "I have a refund receipt from {merchant} dated {later_date} for {amount}. It said the "
       "money would be back in five days. It has now been {days} days."),
    _t("13.6-amb-h", "13.6", "held_out", "ambiguous", RETAIL, ONLINE,
       "{merchant} admitted the {item} was lost in transit and sent written confirmation "
       "of a {amount} credit on {later_date}. {days} days later there is no credit.", alt="13.1"),
    _t("13.7-h", "13.7", "held_out", "standard", ("hotel", "moving"), ("phone",),
       "I called {merchant} on {earlier_date} to cancel my booking and was told there would be no "
       "charge. Then {amount} was taken from my card."),
    _t("13.7-amb-h", "13.7", "held_out", "ambiguous", ("meal_kits",), ONLINE,
       "{merchant} signs you up for repeat deliveries by default, but I only bought one "
       "{item} and cancelled that order on {earlier_date}, before dispatch. I was still charged "
       "{amount}.", alt="13.2"),
]  # fmt: skip

TEMPLATES = DEV_TEMPLATES + HELD_OUT_TEMPLATES


def _round_half_up(x: float) -> int:
    # Python's round() rounds 2.5 to 2; quotas should not depend on that.
    return int(x + 0.5)


def _spread(total: int, codes: list[str]) -> dict[str, int]:
    """Split ``total`` over codes as evenly as possible, extras to the first codes."""
    base, extra = divmod(total, len(codes))
    return {code: base + (1 if i < extra else 0) for i, code in enumerate(codes)}


def _plan_slots(n: int) -> list[tuple[str, str, str]]:
    """Fixed quotas of (code, difficulty, split), before any text is written."""
    codes = list(REASON_CODES)
    per_code = _spread(n, codes)
    ambiguous = _spread(_round_half_up(AMBIGUOUS_SHARE * n), codes)
    slots = []
    for code in codes:
        cells = {"standard": per_code[code] - ambiguous[code], "ambiguous": ambiguous[code]}
        for difficulty, size in cells.items():
            held = _round_half_up(HELD_OUT_SHARE * size)
            if difficulty == "standard" and (held == 0 or held == size):
                raise ValueError(f"n={n} is too small: code {code} cannot fill both splits")
            slots += [(code, difficulty, "held_out")] * held
            slots += [(code, difficulty, "dev")] * (size - held)
    return slots


def _human_date(d: dt.date) -> str:
    return f"{d.day} {MONTHS[d.month - 1]}"


def _add_typos(text: str, protected: set[str], rng: random.Random) -> str:
    """Swap two inner letters in one or two words. Never digits or protected words."""
    words = text.split(" ")
    candidates = [
        i for i, w in enumerate(words) if w.isalpha() and len(w) >= 5 and w.lower() not in protected
    ]
    for i in rng.sample(candidates, k=min(len(candidates), rng.choice([1, 2]))):
        w = words[i]
        j = rng.randrange(1, len(w) - 2)  # keep first and last letter
        words[i] = w[:j] + w[j + 1] + w[j] + w[j + 2 :]
    return " ".join(words)


def _make_case(template: Template, rng: random.Random, fake: Faker) -> dict:
    category_name = rng.choice(template.categories)
    category = CATEGORIES[category_name]
    merchant = f"{fake.random_element(MERCHANT_PREFIXES)} {category.suffix}"
    item = rng.choice(category.items)
    amount = fake.random_int(category.min_usd * 100, category.max_usd * 100) / 100
    correct_amount = round(amount * rng.uniform(*template.correct_ratio), 2)
    # {date} is always the disputed transaction (= transaction_date). Events before it
    # (a cancellation) use {earlier_date}; events after it (a refund) use {later_date}.
    date = fake.date_between_dates(DATE_START, DATE_END)
    offset = dt.timedelta(days=rng.randint(5, 25))

    claim = template.text.format(
        merchant=merchant,
        item=item,
        amount=f"{amount:.2f}",
        correct_amount=f"{correct_amount:.2f}",
        date=_human_date(date),
        earlier_date=_human_date(date - offset),
        later_date=_human_date(date + offset),
        days=rng.randint(6, 30),  # how long the cardholder has waited
        weeks=rng.randint(3, 8),
    )
    tone = rng.choice(list(OPENERS))
    claim = rng.choice(OPENERS[tone]) + claim + rng.choice(CLOSERS[tone])
    if rng.random() < 0.3:
        claim += " " + rng.choice(EXTRA_DETAILS)
    if rng.random() < TYPO_RATE:
        protected = {w.lower() for w in f"{merchant} {item}".split()}
        claim = _add_typos(claim, protected, rng)

    return {
        "split": template.split,
        "difficulty": template.difficulty,
        "channel": rng.choice(template.channels),
        "amount_usd": amount,
        "merchant": merchant,
        "mcc": category.mcc,
        "transaction_date": date.isoformat(),
        "cardholder_claim": claim,
        "label_reason_code": template.label,
        "alt_reason_code": template.alt_reason_code,
        "template_id": template.template_id,
    }


def generate_disputes(n: int, seed: int) -> list[dict]:
    """Generate ``n`` labelled synthetic disputes. Same seed, same output."""
    rng = random.Random(seed)
    fake = Faker("en_US")
    fake.seed_instance(seed)

    slots = _plan_slots(n)
    rng.shuffle(slots)
    pools: dict[tuple[str, str, str], list[Template]] = {}
    for t in TEMPLATES:
        pools.setdefault((t.label, t.difficulty, t.split), []).append(t)
    used = dict.fromkeys(pools, 0)

    cases = []
    for number, key in enumerate(slots, start=1):
        pool = pools[key]
        template = pool[used[key] % len(pool)]  # cycle so every template is used
        used[key] += 1
        cases.append({"case_id": f"S-{number:04d}", **_make_case(template, rng, fake)})
    return cases
