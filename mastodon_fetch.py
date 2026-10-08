import os
import re
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.environ["MASTODON_BASE_URL"].rstrip("/")
TOKEN = os.environ["MASTODON_ACCESS_TOKEN"]
MY_ACCT = "angelashiyu" 

def html_to_text(html: str) -> str:
    # Strip tags + decode entities
    soup = BeautifulSoup(html or "", "html.parser")
    return soup.get_text(" ", strip=True)

def mastodon_get(path: str, params: dict | None = None) -> dict | list:
    url = f"{BASE_URL}{path}"
    headers = {"Authorization": f"Bearer {TOKEN}"}
    r = requests.get(url, headers=headers, params=params, timeout=30)
    r.raise_for_status()
    return r.json()

def fetch_recent_statuses_for_keyword(keyword: str, limit: int = 5) -> list[dict]:
    """
    Try full-text search first (/api/v2/search). If empty, fall back to hashtag timeline.
    """
    # 1) Try /api/v2/search (statuses)
    # Docs: /api/v2/search supports type=statuses and limit.
    try:
        data = mastodon_get("/api/v2/search", params={"q": keyword, "type": "statuses", "limit": limit})
        statuses = data.get("statuses", []) if isinstance(data, dict) else []
    except requests.HTTPError:
        statuses = []

    if statuses:
        return statuses[:limit]

    # 2) Fallback: hashtag timeline (more reliable than keyword search)
    # Docs: /api/v1/timelines/tag/:hashtag
    words = re.findall(r"\w+", keyword)
    hashtag_candidates = dict.fromkeys(["".join(words), "_".join(words)])  # "AI SEO" -> AISEO, AI_SEO
    for tag in hashtag_candidates:
        try:
            statuses = mastodon_get(f"/api/v1/timelines/tag/{tag}", params={"limit": limit})
            if statuses:
                return statuses[:limit]
        except requests.HTTPError:
            continue

    return []

def normalize_statuses(raw_statuses: list[dict]) -> list[dict]:
    """
    Keep only what we need for LLM reply generation.
    """
    out = []
    for s in raw_statuses:
        if s.get("account", {}).get("acct") == MY_ACCT:
            continue
        out.append({
            "id": s["id"],
            "url": s.get("url"),
            "author": s.get("account", {}).get("acct"),
            "content_text": html_to_text(s.get("content", "")),
            "language": s.get("language"),
        })
    return out

if __name__ == "__main__":
    raw = fetch_recent_statuses_for_keyword("AI SEO", limit=10)
    statuses = normalize_statuses(raw)
    print(f"Found {len(statuses)} statuses")
    for i, s in enumerate(statuses, 1):
        print(f"\n#{i} {s['url']}\n{s['content_text']}\n")