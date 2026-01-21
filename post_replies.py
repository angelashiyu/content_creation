import time
from mastodon_post import post_status

REPLIES = [
    {"in_reply_to_id": "115932457200189987",
     "reply_text": "Congrats on the funding. As AI answers dominate search, tracking how LLMs reference your brand becomes key. Our platform surfaces those mentions, highlights gaps, and suggests actions — helping you prove the ROI of that visibility."},

    {"in_reply_to_id": "115932255596294099",
     "reply_text": "Totally agree — clarity beats buzz. In an AI-first search world, brands that monitor how LLMs surface them can pivot quickly. Measuring those mentions helps keep the message human while staying visible."},

    {"in_reply_to_id": "115932100466714405",
     "reply_text": "Free AI writers are handy, but the real advantage is ensuring the content shows up in AI answers. We help brands track those citations and prioritize SEO actions that keep their content in the mix."},

    {"in_reply_to_id": "115931395100998604",
     "reply_text": "Exactly — search is shifting to AI recommendations. Brands need to watch how AI describes them and why they might be omitted. Our tool flags missing mentions and suggests fixes before visibility drops."},

    {"in_reply_to_id": "115930933732968085",
     "reply_text": "Interesting experiment. Low-cost AI SEO can boost visibility, but without tracking AI citations you won’t know if the traffic translates into brand mentions. Monitoring those signals can guide smarter optimizations."},
]

def main():
    for r in REPLIES:
        resp = post_status(
            r["reply_text"],
            visibility="public",
            in_reply_to_id=r["in_reply_to_id"]
        )
        print("Replied:", resp.get("url") or resp.get("id"))
        time.sleep(1)

if __name__ == "__main__":
    main()