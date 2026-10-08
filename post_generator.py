from llm import BRAND_VOICE, complete

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
Return ONLY the post text.
""".strip()

    return complete(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        model=model,
    )
