import pytest

from atlas.parsing import parse_reply


@pytest.mark.parametrize(
    "text",
    [
        '{"reason_code": "13.1", "confidence": 0.8}',
        '```json\n{"reason_code": "13.1"}\n```',
        'Here you go: {"reason_code": "13.1"} thanks',
        'Use {braces} carefully. {"reason_code": "13.1"}',
    ],
)
def test_extracts_json_wrapped_in_noise(text):
    assert parse_reply(text)["reason_code"] == "13.1"


def test_returns_the_first_of_two_objects():
    text = '{"reason_code": "13.1"} and later {"reason_code": "13.6"}'

    assert parse_reply(text) == {"reason_code": "13.1"}


@pytest.mark.parametrize("text", [None, "", "mock reply", "{not json}", "[1, 2]", '{"a": 1'])
def test_returns_none_without_a_json_object(text):
    assert parse_reply(text) is None
