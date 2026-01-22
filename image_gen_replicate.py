import os
from dotenv import load_dotenv
from pathlib import Path
import replicate

load_dotenv(dotenv_path=Path(__file__).with_name(".env"))

MODEL_ID = "sundai-club/ai_seo_promo_pics:0dfeb4c2070249fcb7306f098fa13cdc2a3fd35eff48d5b05f7988b4621f53d0"
TRIGGER = "ANGZIKI9"
MASTODON_BASE_URL = os.environ["MASTODON_BASE_URL"]
MASTODON_ACCESS_TOKEN = os.environ["MASTODON_ACCESS_TOKEN"]

def generate_image(scene: str, fast: bool = True) -> str:
    """
    Returns an image URL.
    scene: what you want the subject doing / style
    fast: use schnell (4 steps) vs dev (28 steps)
    """
    prompt = f"{TRIGGER} {scene}"

    if fast:
        inputs = {
            "prompt": prompt,
            "model": "schnell",
            "num_inference_steps": 4,
            "guidance_scale": 7.5,
        }
    else:
        inputs = {
            "prompt": prompt,
            "model": "dev",
            "num_inference_steps": 28,
            "guidance_scale": 7.5,
        }

    out = replicate.run(MODEL_ID, input=inputs)
    return str(out[0])  # Replicate returns a list of URLs

import requests

def upload_media_from_url(image_url: str, alt_text: str = "") -> str:
    img_bytes = requests.get(image_url, timeout=60).content

    # Upload to Mastodon (v2 recommended; v1 works but is deprecated) :contentReference[oaicite:3]{index=3}
    files = {"file": ("image.png", img_bytes)}
    data = {}
    if alt_text:
        data["description"] = alt_text  # supported on v1; many instances also accept on v2

    r = requests.post(
        f"{MASTODON_BASE_URL}/api/v2/media",
        headers={"Authorization": f"Bearer {MASTODON_ACCESS_TOKEN}"},
        files=files,
        data=data,
        timeout=60,
    )
    r.raise_for_status()
    media = r.json()
    return media["id"]

def post_status_with_media(text: str, media_id: str, visibility="public", in_reply_to_id=None):
    data = {"status": text, "visibility": visibility, "media_ids[]": [media_id]}
    if in_reply_to_id:
        data["in_reply_to_id"] = in_reply_to_id

    r = requests.post(
        f"{MASTODON_BASE_URL}/api/v1/statuses",
        headers={"Authorization": f"Bearer {MASTODON_ACCESS_TOKEN}"},
        data=data,
        timeout=30,
    )
    r.raise_for_status()
    return r.json()

img_url = generate_image("black dog in a clean vector icon style, favicon, white background")
media_id = upload_media_from_url(img_url, alt_text="Vector icon of a black dog (favicon style)")
resp = post_status_with_media("Testing my fine-tuned model 🔥", media_id)
print("Posted:", resp.get("url"))
