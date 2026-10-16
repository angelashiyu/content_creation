"""Generation code with the model call replaced, so nothing reaches OpenRouter."""
import json

import pytest

import generate_replies
import mastodon_post
import post_generator
from llm import parse_json_object


def test_parse_json_object_ignores_code_fences():
    assert parse_json_object('```json\n{"a": 1}\n```') == {"a": 1}


def test_parse_json_object_raises_without_json():
    with pytest.raises(ValueError):
        parse_json_object("Sorry, I can't help with that.")


@pytest.mark.parametrize("raw, flag", [(True, True), ("true", True), (" TRUE ", True),
                                       (False, False), ("false", False), (None, False), ("yes", False)])
def test_review_flag_accepts_string_booleans(monkeypatch, raw, flag):
    reply = {"in_reply_to_id": "1", "reply_text": "hi", "requires_review": raw}
    monkeypatch.setattr(generate_replies, "complete", lambda *a, **k: json.dumps({"replies": [reply]}))
    batch = generate_replies.generate_replies([{"id": "1", "content_text": "hello"}])
    assert batch["replies"][0]["requires_review"] is flag


@pytest.mark.parametrize("raw, expected", [
    ("NO_POST", "NO_POST"),
    ("NO_POST\n", "NO_POST"),
    ("A real post about AI SEO.", "A real post about AI SEO."),
])
def test_post_generator_normalizes_a_decline(monkeypatch, raw, expected):
    monkeypatch.setattr(post_generator, "complete", lambda *a, **k: raw)
    assert post_generator.generate_post("context", topic="AI SEO") == expected


class _Response:
    def __init__(self, status, headers=None):
        self.status_code, self.headers = status, headers or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)

    def json(self):
        return {"id": "42"}


def test_post_status_retries_a_429_a_bounded_number_of_times(monkeypatch):
    calls, sleeps = [], []
    monkeypatch.setattr(mastodon_post.requests, "post", lambda *a, **k: calls.append(1) or _Response(429))
    monkeypatch.setattr(mastodon_post.time, "sleep", sleeps.append)
    with pytest.raises(RuntimeError):
        mastodon_post.post_status("hello")
    assert len(calls) == mastodon_post.MAX_RETRIES + 1
    assert len(sleeps) == mastodon_post.MAX_RETRIES


def test_post_status_succeeds_after_a_429(monkeypatch):
    responses = iter([_Response(429, {"Retry-After": "Wed, 21 Oct 2026 07:28:00 GMT"}), _Response(200)])
    sleeps = []
    monkeypatch.setattr(mastodon_post.requests, "post", lambda *a, **k: next(responses))
    monkeypatch.setattr(mastodon_post.time, "sleep", sleeps.append)
    assert mastodon_post.post_status("hello") == {"id": "42"}
    assert sleeps == [5]  # an HTTP-date Retry-After falls back to 5 seconds
