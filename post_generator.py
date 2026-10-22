from llm import BRAND_VOICE, complete

# returned instead of a post when the company context cannot support the topic
NO_POST = "NO_POST"


def generate_post(context, topic="AI SEO", max_words=80, model=None):
    system = (
        "You write social posts for a GenAI marketing intelligence platform.\n"
        f"Voice: {BRAND_VOICE}\n"
        "Rules: no 'DM me'. Keep it tight.\n"
    )

    user = f"""
Company context:
{context}

Task:
Write ONE Mastodon post about: {topic}
- {max_words} words max
- 1 short hook line
- 2-4 concise bullet points OR 2 short paragraphs
- Optional: 1 relevant hashtag (max 2)
- Use only facts stated in the company context. Never invent prices, plans, customers, numbers or results.
- Decline only when the topic asks for prices, plans, customer names or customer results that the company context does not contain: then return exactly {NO_POST} and nothing else. For any other topic, write the post from what the context supports.
Return ONLY the post text, or {NO_POST}.
""".strip()

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    post = complete(messages, model=model)

    if NO_POST in post:
        return NO_POST
    return post
