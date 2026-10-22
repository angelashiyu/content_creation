import json
import os
import requests
from dotenv import load_dotenv

load_dotenv()

HEADERS = {
    "Authorization": "Bearer " + os.environ["NOTION_TOKEN"],
    "Notion-Version": "2022-06-28",
}

# Notion block types that hold normal text
TEXT_BLOCKS = [
    "paragraph", "heading_1", "heading_2", "heading_3",
    "bulleted_list_item", "numbered_list_item", "to_do", "quote", "callout",
]


def rich_text_to_plain(rich_text):
    parts = []
    for piece in rich_text or []:
        parts.append(piece.get("plain_text", ""))
    return "".join(parts).strip()


def block_text(block):
    block_type = block.get("type")
    content = block.get(block_type, {})

    if block_type in TEXT_BLOCKS:
        return rich_text_to_plain(content.get("rich_text"))
    if block_type == "code":
        code = rich_text_to_plain(content.get("rich_text"))
        language = content.get("language", "")
        return "```" + language + "\n" + code + "\n```"
    return ""


def get_block_children(block_id):
    # Notion sends at most 100 blocks per request, so keep asking until has_more is false
    url = f"https://api.notion.com/v1/blocks/{block_id}/children"
    params = {"page_size": 100}
    blocks = []
    while True:
        r = requests.get(url, headers=HEADERS, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        blocks.extend(data["results"])
        if not data["has_more"]:
            return blocks
        params["start_cursor"] = data["next_cursor"]


def fetch_page_text(page_id):
    lines = []
    for block in get_block_children(page_id):
        text = block_text(block)
        if text:
            lines.append(text)
    # blank line between blocks so the paragraph chunker can split them
    return "\n\n".join(lines).strip()


def get_context_text(config_path="config.json"):
    with open(config_path, encoding="utf-8") as f:
        config = json.load(f)
    page_id = config["notion"]["overview_page_id"].replace("-", "")
    return fetch_page_text(page_id)
