from llm import BRAND_VOICE, complete

# returned instead of a post when the company context cannot support the topic
NO_POST = "NO_POST"

def generate_post(context: str, topic: str = "AI SEO", max_words: int = 80, model: str | None = None) -> str:
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
- If the topic asks for facts the company context does not contain (for example prices or customer results), do not write a post. Return exactly {NO_POST} and nothing else.
Return ONLY the post text, or {NO_POST}.
""".strip()

    post = complete(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        model=model,
    )
    return NO_POST if NO_POST in post else post
