from dotenv import load_dotenv
from pathlib import Path
import replicate
from mastodon_post import post_status, upload_media_from_url

load_dotenv(dotenv_path=Path(__file__).with_name(".env"))

MODEL_ID = "sundai-club/ai_seo_promo_pics:0dfeb4c2070249fcb7306f098fa13cdc2a3fd35eff48d5b05f7988b4621f53d0"
TRIGGER = "ANGZIKI9"

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

if __name__ == "__main__":
    img_url = generate_image("black dog in a clean vector icon style, favicon, white background")
    media_id = upload_media_from_url(img_url, alt_text="Vector icon of a black dog (favicon style)")
    resp = post_status("Testing my fine-tuned model 🔥", visibility="public", media_ids=[media_id])
    print("Posted:", resp.get("url"))
