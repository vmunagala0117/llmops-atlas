"""Pull a JSON answer out of a model reply."""

import json

_decoder = json.JSONDecoder()


def parse_reply(text: str | None) -> dict | None:
    """Return the first JSON object in ``text``, or None if there is none.

    Models often wrap JSON in prose or ``` fences, so try each ``{`` in turn
    instead of parsing the whole reply.
    """
    if not text:
        return None
    start = text.find("{")
    while start != -1:
        try:
            obj, _ = _decoder.raw_decode(text, start)
            return obj  # starts at "{", so always a dict
        except ValueError:
            start = text.find("{", start + 1)
    return None
