"""LLM-as-judge: scores a piece of output 1-5 on each rubric criterion."""
import json
import re

from llm import BRAND_VOICE, complete

POST_RUBRIC = {
    "grounded": "Every claim about the company or product is supported by the company context. Nothing invented (stats, customers, pricing, features).",
    "voice": BRAND_VOICE,
    "value": "A reader learns something concrete or gets a useful frame. Not generic filler.",
    "on_topic": "The post is about the requested topic.",
}

REPLY_RUBRIC = {
    "relevant": "Responds to what the status actually says.",
    "value": "Adds value: answers, clarifies, or offers a useful frame (or asks ONE short question if the status is unclear).",
    "not_salesy": "Does not pitch a product or company.",
    "voice": BRAND_VOICE,
}

MIN_PASSING_SCORE = 3


def judge(rubric: dict[str, str], material: str, model: str) -> dict:
    """Returns {"scores": {criterion: 1..5}, "notes": str}. Raises if the judge output is unusable."""
    criteria = "\n".join(f"- {name}: {desc}" for name, desc in rubric.items())
    shape = {**dict.fromkeys(rubric, 0), "notes": "one sentence on the weakest criterion"}
    prompt = f"""You are a strict evaluator of social media copy.
Score the output on each criterion from 1 (fails) to 5 (excellent). 3 means acceptable.

Criteria:
{criteria}

{material}

Return ONLY valid JSON (no markdown) matching this shape, with integer scores:
{json.dumps(shape)}"""

    raw = complete(prompt, model=model)
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        raise ValueError(f"judge returned no JSON: {raw[:200]!r}")
    data = json.loads(match.group(0))
    scores = {name: int(data[name]) for name in rubric}
    if not all(1 <= s <= 5 for s in scores.values()):
        raise ValueError(f"judge scores out of range: {scores}")
    return {"scores": scores, "notes": str(data.get("notes", ""))}
