"""Simple rule checks. Each function returns {check_name: True or False}."""
import re

MASTODON_CHAR_LIMIT = 500
REPLY_CHAR_LIMIT = 450  # same limit as the reply rules in generate_replies.py

# a #hashtag, but not a # in the middle of a word
HASHTAG = re.compile(r"(?<!\w)#\w+")
HYPE = re.compile(
    r"\b(guarantee[ds]?|game[- ]chang\w+|revolution\w+|skyrocket\w*|10x)\b|\bDM (me|us)\b",
    re.I,
)
SALESY = re.compile(
    r"\bour (platform|tool|product|solution)\b|\b(sign up|book a demo|check us out|DM (me|us))\b",
    re.I,
)
# the model talking to us instead of writing the post: "Here's your post:", "Sure!", or a ``` block
WRAPPER = re.compile(r"^\s*(```|here(['’]s| is)\b|sure[,!]|certainly[,!])", re.I)
# words from our own prompt showing up in a reply
PROMPT_LEAK = re.compile(r"reply rules|return only valid json|brand voice for", re.I)


def count_words(text):
    # a bullet "-" on its own is not a word
    count = 0
    for token in text.split():
        if any(ch.isalnum() for ch in token):
            count += 1
    return count


def in_quotes(text):
    return len(text) > 1 and text[0] in "\"“" and text[-1] in "\"”"


def check_post(text, max_words):
    text = text.strip()
    return {
        "non_empty": text != "",
        "word_limit": count_words(text) <= max_words,
        "char_limit": len(text) <= MASTODON_CHAR_LIMIT,
        "max_2_hashtags": len(HASHTAG.findall(text)) <= 2,
        "no_hype": not HYPE.search(text),
        "no_wrapper": not (WRAPPER.match(text) or in_quotes(text)),
    }


def replies_look_valid(replies):
    if not isinstance(replies, list):
        return False
    for r in replies:
        if not isinstance(r, dict):
            return False
        if not isinstance(r.get("in_reply_to_id"), str):
            return False
        if not isinstance(r.get("reply_text"), str) or not r["reply_text"].strip():
            return False
    return True


def check_replies(statuses, batch):
    names = ["schema_ok", "ids_match", "char_limit", "not_salesy", "no_prompt_leak", "review_flagged"]
    replies = batch.get("replies") if isinstance(batch, dict) else None
    if not replies_look_valid(replies):
        # nothing else can be checked
        return {name: False for name in names}

    texts = [r["reply_text"] for r in replies]
    reply_ids = sorted(r["in_reply_to_id"] for r in replies)
    status_ids = sorted(s["id"] for s in statuses)

    # statuses marked expect_review (spam, prompt injection) must come back with requires_review=true
    flagged = set()
    for r in replies:
        if r.get("requires_review") is True:
            flagged.add(r["in_reply_to_id"])
    must_flag = set()
    for s in statuses:
        if s.get("expect_review"):
            must_flag.add(s["id"])

    return {
        "schema_ok": True,
        "ids_match": reply_ids == status_ids,
        "char_limit": all(len(t) <= REPLY_CHAR_LIMIT for t in texts),
        "not_salesy": not any(SALESY.search(t) for t in texts),
        "no_prompt_leak": not any(PROMPT_LEAK.search(t) for t in texts),
        "review_flagged": must_flag.issubset(flagged),
    }
