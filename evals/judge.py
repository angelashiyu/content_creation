"""LLM-as-judge: another LLM call scores an output from 1 to 5 on each criterion."""
import json
from llm import BRAND_VOICE, complete, parse_json_object

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


def judge(rubric, material, model):
    """Returns {"scores": {criterion: 1-5}, "notes": "..."}. Raises an error if the judge's answer is unusable."""
    criteria_lines = []
    for name, description in rubric.items():
        criteria_lines.append(f"- {name}: {description}")
    criteria = "\n".join(criteria_lines)

    # the JSON we want back, e.g. {"grounded": 0, "voice": 0, ..., "notes": "..."}
    shape = {}
    for name in rubric:
        shape[name] = 0
    shape["notes"] = "one sentence on the weakest criterion"

    prompt = f"""You are a strict evaluator of social media copy.
Score the output on each criterion from 1 (fails) to 5 (excellent). 3 means acceptable.

Criteria:
{criteria}

{material}

Return ONLY valid JSON (no markdown) matching this shape, with integer scores:
{json.dumps(shape)}"""

    data = parse_json_object(complete(prompt, model=model))

    scores = {}
    for name in rubric:
        score = int(data[name])
        if score < 1 or score > 5:
            raise ValueError(f"judge score out of range: {name}={score}")
        scores[name] = score
    return {"scores": scores, "notes": str(data.get("notes", ""))}
