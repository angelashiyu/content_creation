import os
from dotenv import load_dotenv
from pathlib import Path
from openai import OpenAI

load_dotenv(dotenv_path=Path(__file__).with_name(".env"))

client = OpenAI(
    api_key=os.environ["OPENROUTER_API_KEY"],
    base_url="https://openrouter.ai/api/v1",
)

DEFAULT_MODEL = os.environ.get("OPENROUTER_MODEL", "nvidia/nemotron-3-nano-30b-a3b:free")

def generate_post(context: str, topic: str = "AI SEO", max_words: int = 80) -> str:
    system = (
        "You write social posts for a GenAI marketing intelligence platform.\n"
        "Voice: analytical, practical, direct, slightly opinionated, optimistic.\n"
        "Rules: no hype, no guarantees, no 'DM me'. Keep it tight.\n"
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

    resp = client.responses.create(
        model=DEFAULT_MODEL,
        input=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return resp.output_text.strip()