import json
from pathlib import Path

STATE_FILE = Path("posted.json")

def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"posts": []}

def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2))

def already_posted(text: str) -> bool:
    state = load_state()
    return text in state["posts"]

def mark_posted(text: str):
    state = load_state()
    state["posts"].append(text)
    save_state(state)