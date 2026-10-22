import json
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

DEFAULT_MODEL = os.environ.get("OPENROUTER_MODEL", "nvidia/nemotron-3-super-120b-a12b:free")

BRAND_VOICE = "Analytical, practical, direct, slightly opinionated, optimistic. No hype. No guarantees."


def complete(prompt, model=None):
    # OpenRouter speaks the same API as OpenAI, so the openai library works with a different URL
    client = OpenAI(api_key=os.environ["OPENROUTER_API_KEY"], base_url="https://openrouter.ai/api/v1")
    response = client.responses.create(model=model or DEFAULT_MODEL, input=prompt)
    return response.output_text.strip()


def parse_json_object(text):
    # models sometimes add ``` or extra words around the JSON, so cut out the {...} part
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end < start:
        raise ValueError("model returned no JSON object: " + text[:200])
    return json.loads(text[start:end + 1])
