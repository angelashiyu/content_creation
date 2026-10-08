import json
from llm import BRAND_VOICE, complete

BRAND_DOCS = f"""\
You are the brand voice for a GenAI marketing intelligence platform.
We help brands gain visibility inside AI-generated answers by measuring how LLMs mention them, diagnosing why they’re missing, and generating prioritized actions to improve their presence.

Voice: {BRAND_VOICE}
Reply rules:
- Add value (answer, clarify, or share a helpful frame).
- Do NOT be salesy.
- If unclear, ask ONE short question.
- Keep reply_text <= 450 characters.
"""

SCHEMA_SHAPE = {
  "replies": [
    {
      "in_reply_to_id": "string",
      "reply_text": "string",
      "tone": "friendly|helpful|curious",
      "requires_review": False,
      "reasons": ["none"]
    }
  ]
}

def generate_replies(statuses, model: str | None = None):
    prompt = f"""
{BRAND_DOCS}

Return ONLY valid JSON (no markdown, no extra text) matching this shape:
{json.dumps(SCHEMA_SHAPE)}

Statuses to reply to (your in_reply_to_id must match each status id):
{json.dumps(statuses, ensure_ascii=False)}
"""

    raw = complete(prompt, model=model)
    return json.loads(raw)

if __name__ == "__main__":
    test_statuses = [
        {"id": "123", "author": "someone", "text": "AI SEO feels chaotic—how do you measure impact?", "url": "", "language": "en"},
        {"id": "456", "author": "other", "text": "Any practical checklist for showing up in LLM answers?", "url": "", "language": "en"},
    ]
    print(generate_replies(test_statuses))