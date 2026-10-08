import os
from functools import cache
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

DEFAULT_MODEL = os.environ.get("OPENROUTER_MODEL", "nvidia/nemotron-3-super-120b-a12b:free")

BRAND_VOICE = "Analytical, practical, direct, slightly opinionated, optimistic. No hype. No guarantees."

@cache
def _client() -> OpenAI:
    # built on first use so importing this module doesn't need the API key
    return OpenAI(
        api_key=os.environ["OPENROUTER_API_KEY"],
        base_url="https://openrouter.ai/api/v1",
    )

def complete(prompt: str | list[dict], model: str | None = None) -> str:
    resp = _client().responses.create(model=model or DEFAULT_MODEL, input=prompt)
    return resp.output_text.strip()
