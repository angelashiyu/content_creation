from mastodon_fetch import fetch_recent_statuses_for_keyword, normalize_statuses
from generate_replies import generate_replies

def main():
    statuses = normalize_statuses(fetch_recent_statuses_for_keyword("AI SEO", limit=20))[:5]
    if not statuses:
        print("No statuses found.")
        return

    batch = generate_replies(statuses)
    for i, r in enumerate(batch["replies"], 1):
        print(f"\nReply #{i}")
        print("in_reply_to_id:", r["in_reply_to_id"])
        print("text:", r["reply_text"])
        print("requires_review:", r["requires_review"], "reasons:", r["reasons"])

if __name__ == "__main__":
    main()