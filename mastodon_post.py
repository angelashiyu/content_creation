import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.environ["MASTODON_BASE_URL"].rstrip("/")
HEADERS = {"Authorization": "Bearer " + os.environ["MASTODON_ACCESS_TOKEN"]}
MAX_RETRIES = 3  # when Mastodon says 429 (too many requests)


def wait_seconds(response):
    # Retry-After is usually a number of seconds, but it can also be a date
    value = response.headers.get("Retry-After", "5")
    if value.isdigit():
        return int(value)
    return 5


def post_status(text, visibility=None, in_reply_to_id=None, media_ids=None):
    data = {"status": text}
    if visibility:
        data["visibility"] = visibility  # public, unlisted, private or direct
    if in_reply_to_id:
        data["in_reply_to_id"] = in_reply_to_id
    if media_ids:
        data["media_ids[]"] = media_ids

    url = BASE_URL + "/api/v1/statuses"
    r = requests.post(url, headers=HEADERS, data=data, timeout=30)

    # a 429 means nothing was posted, so waiting and trying again can't post twice
    retries = 0
    while r.status_code == 429 and retries < MAX_RETRIES:
        time.sleep(wait_seconds(r))
        r = requests.post(url, headers=HEADERS, data=data, timeout=30)
        retries += 1

    r.raise_for_status()
    return r.json()


def upload_media_from_url(image_url, alt_text=""):
    image = requests.get(image_url, timeout=60)
    image.raise_for_status()

    data = {}
    if alt_text:
        data["description"] = alt_text
    r = requests.post(
        BASE_URL + "/api/v2/media",
        headers=HEADERS,
        files={"file": ("image.png", image.content)},
        data=data,
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["id"]


def post_batch(posts, visibility="unlisted", dry_run=True):
    """posts: list of dicts like {"text": ..., "hashtags": [...], "requires_review": False}"""
    for i, p in enumerate(posts, start=1):
        if p.get("requires_review"):
            print(f"[SKIP review] #{i}: {p.get('text', '')[:80]}…")
            continue

        text = (p.get("text") or "").strip()
        hashtags = p.get("hashtags") or []
        if hashtags:
            text = text + "\n\n" + " ".join(hashtags)

        if dry_run:
            print(f"[DRY RUN] #{i}:\n{text}\n---\n")
            continue

        response = post_status(text, visibility=visibility)
        print("Posted:", response.get("url") or response.get("id"))
        time.sleep(1)


if __name__ == "__main__":
    example = [{
        "text": "AI answer visibility ≠ classic SEO. Start by measuring mentions + citations across a consistent prompt set.",
        "hashtags": ["#MarketingIntelligence", "#LLM"],
        "requires_review": False,
    }]
    post_batch(example, visibility="unlisted", dry_run=True)  # dry_run=False to really post
