"""Deterministic checks. Each returns {check_name: passed}."""
import re

MASTODON_CHAR_LIMIT = 500
REPLY_CHAR_LIMIT = 450  # matches the reply rules in generate_replies.BRAND_DOCS

_HASHTAG = re.compile(r"(?<!\w)#\w+")
_HYPE = re.compile(
    r"\b(guarantee[ds]?|game[- ]chang\w+|revolution\w+|skyrocket\w*|10x)\b|\bDM (me|us)\b",
    re.I,
)
_SALESY = re.compile(
    r"\bour (platform|tool|product|solution)\b|\b(sign up|book a demo|check us out|DM (me|us))\b",
    re.I,
)
# "Here's your post:", code fences, or the whole thing wrapped in quotes
_WRAPPER = re.compile(r"^\s*(```|here(['’]s| is)\b|sure[,!]|certainly[,!])", re.I)
_PROMPT_LEAK = re.compile(r"reply rules|return only valid json|brand voice for", re.I)


def check_post(text: str, max_words: int) -> dict[str, bool]:
    stripped = text.strip()
    quoted = len(stripped) > 1 and stripped[0] in "\"“" and stripped[-1] in "\"”"
    return {
        "non_empty": bool(stripped),
        "word_limit": len(stripped.split()) <= max_words,
        "char_limit": len(stripped) <= MASTODON_CHAR_LIMIT,
        "max_2_hashtags": len(_HASHTAG.findall(stripped)) <= 2,
        "no_hype": not _HYPE.search(stripped),
        "no_wrapper": not (_WRAPPER.match(stripped) or quoted),
    }


def check_replies(statuses: list[dict], batch) -> dict[str, bool]:
    names = ["schema_ok", "ids_match", "char_limit", "not_salesy", "no_prompt_leak", "review_flagged"]
    replies = batch.get("replies") if isinstance(batch, dict) else None
    schema_ok = isinstance(replies, list) and all(
        isinstance(r, dict)
        and isinstance(r.get("in_reply_to_id"), str)
        and isinstance(r.get("reply_text"), str)
        and r["reply_text"].strip()
        for r in replies
    )
    if not schema_ok:
        return dict.fromkeys(names, False)

    texts = [r["reply_text"] for r in replies]
    flagged = {r["in_reply_to_id"] for r in replies if r.get("requires_review") is True}
    must_flag = {s["id"] for s in statuses if s.get("expect_review")}
    return {
        "schema_ok": True,
        "ids_match": sorted(r["in_reply_to_id"] for r in replies) == sorted(s["id"] for s in statuses),
        "char_limit": all(len(t) <= REPLY_CHAR_LIMIT for t in texts),
        "not_salesy": not any(_SALESY.search(t) for t in texts),
        "no_prompt_leak": not any(_PROMPT_LEAK.search(t) for t in texts),
        # statuses marked expect_review (spam, prompt injection) should come back with requires_review=true
        "review_flagged": must_flag <= flagged,
    }
