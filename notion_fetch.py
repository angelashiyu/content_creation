import os, json, requests
from dotenv import load_dotenv
from pathlib import Path
from bs4 import BeautifulSoup

load_dotenv(dotenv_path=Path(__file__).with_name(".env"))

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
NOTION_VERSION = "2022-06-28"

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": NOTION_VERSION,
    "Content-Type": "application/json",
}

def _rich_text_to_plain(rich_text: list[dict]) -> str:
    return "".join(rt.get("plain_text", "") for rt in (rich_text or [])).strip()

def _block_text(block: dict) -> str:
    t = block.get("type")
    obj = block.get(t, {}) if t else {}

    if t in {
        "paragraph", "heading_1", "heading_2", "heading_3",
        "bulleted_list_item", "numbered_list_item", "to_do",
        "quote", "callout"
    }:
        return _rich_text_to_plain(obj.get("rich_text", []))

    if t == "code":
        code = _rich_text_to_plain(obj.get("rich_text", []))
        lang = obj.get("language", "")
        return f"```{lang}\n{code}\n```".strip()

    return ""

def _get_block_children(block_id: str) -> list[dict]:
    results = []
    url = f"https://api.notion.com/v1/blocks/{block_id}/children?page_size=100"
    while True:
        r = requests.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()
        data = r.json()
        results.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        url = f"https://api.notion.com/v1/blocks/{block_id}/children?page_size=100&start_cursor={data['next_cursor']}"
    return results

def fetch_page_text(page_id: str) -> str:
    blocks = _get_block_children(page_id)
    lines = []
    for b in blocks:
        txt = _block_text(b)
        if txt:
            lines.append(txt)
    return "\n".join(lines).strip()

def get_context_text(config_path: str = "config.json") -> str:
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    page_id = cfg["notion"]["overview_page_id"]
    page_id = page_id.replace("-", "")
    return fetch_page_text(page_id)