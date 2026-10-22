import os
import re
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.environ["MASTODON_BASE_URL"].rstrip("/")
TOKEN = os.environ["MASTODON_ACCESS_TOKEN"]
# posts from this account are skipped, so the bot never replies to itself
MY_ACCOUNT = os.environ.get("MASTODON_ACCT", "angelashiyu")


def html_to_text(html):
    # Mastodon sends posts as HTML; keep only the text
    return BeautifulSoup(html or "", "html.parser").get_text(" ", strip=True)


def mastodon_get(path, params=None):
    headers = {"Authorization": "Bearer " + TOKEN}
    r = requests.get(BASE_URL + path, headers=headers, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def fetch_recent_statuses_for_keyword(keyword, limit=5):
    # 1) try full-text search
    try:
        data = mastodon_get("/api/v2/search", params={"q": keyword, "type": "statuses", "limit": limit})
        statuses = data.get("statuses", [])
    except requests.HTTPError:
        statuses = []
    if statuses:
        return statuses[:limit]

    # 2) many servers turn search off, so try hashtags: "AI SEO" -> #AISEO, then #AI_SEO
    words = re.findall(r"\w+", keyword)
    hashtags = ["".join(words)]
    if len(words) > 1:
        hashtags.append("_".join(words))

    for tag in hashtags:
        try:
            statuses = mastodon_get(f"/api/v1/timelines/tag/{tag}", params={"limit": limit})
        except requests.HTTPError:
            continue
        if statuses:
            return statuses[:limit]
    return []


def normalize_statuses(raw_statuses):
    # keep only the fields the reply prompt needs
    statuses = []
    for s in raw_statuses:
        author = s.get("account", {}).get("acct")
        if author == MY_ACCOUNT:
            continue
        statuses.append({
            "id": s["id"],
            "url": s.get("url"),
            "author": author,
            "content_text": html_to_text(s.get("content", "")),
            "language": s.get("language"),
        })
    return statuses


if __name__ == "__main__":
    statuses = normalize_statuses(fetch_recent_statuses_for_keyword("AI SEO", limit=10))
    print(f"Found {len(statuses)} statuses")
    for i, s in enumerate(statuses, start=1):
        print(f"\n#{i} {s['url']}\n{s['content_text']}\n")
