import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.environ["MASTODON_BASE_URL"].rstrip("/")
TOKEN = os.environ["MASTODON_ACCESS_TOKEN"]

def post_status(text: str, visibility: str = "public", in_reply_to_id: str | None = None) -> dict:
    url = f"{BASE_URL}/api/v1/statuses"
    headers = {"Authorization": f"Bearer {TOKEN}"}
    data = {"status": text, "visibility": visibility}  # public|unlisted|private|direct

    r = requests.post(url, headers=headers, data=data, timeout=30)

    # basic rate-limit handling
    if r.status_code == 429:
        retry_after = int(r.headers.get("Retry-After", "5"))
        time.sleep(retry_after)
        return post_status(text, visibility=visibility)

    r.raise_for_status()
    return r.json()

def post_batch(posts: list[dict], visibility: str = "unlisted", dry_run: bool = True):
    """
    posts: list of dicts with keys like {text, hashtags?, requires_review?}
    dry_run=True prints instead of posting.
    """
    for i, p in enumerate(posts, start=1):
        if p.get("requires_review"):
            print(f"[SKIP review] #{i}: {p.get('text','')[:80]}…")
            continue

        text = (p.get("text") or "").strip()
        hashtags = p.get("hashtags") or []
        if hashtags:
            text = text + "\n\n" + " ".join(hashtags)

        if dry_run:
            print(f"[DRY RUN] #{i}:\n{text}\n---\n")
            continue

        resp = post_status(text, visibility=visibility)
        print("Posted:", resp.get("url") or resp.get("id"))
        time.sleep(1)

if __name__ == "__main__":
    payload = {
        "posts": [
            {
                "text": "AI answer visibility ≠ classic SEO. Start by measuring mentions + citations across a consistent prompt set.",
                "hashtags": ["#MarketingIntelligence", "#LLM"],
                "requires_review": False
            }
        ]
    }

    post_batch(payload["posts"], visibility="unlisted", dry_run=True)  # set dry_run=False to actually post