import sys
import replicate
from dotenv import load_dotenv
from mastodon_post import post_status, upload_media_from_url

load_dotenv()

# my fine-tuned image model on Replicate; TRIGGER is the word it was trained on
MODEL_ID = "sundai-club/ai_seo_promo_pics:0dfeb4c2070249fcb7306f098fa13cdc2a3fd35eff48d5b05f7988b4621f53d0"
TRIGGER = "ANGZIKI9"


def generate_image(scene, fast=True):
    """Returns an image URL. fast=True uses the quick "schnell" model, False the slower "dev" one."""
    inputs = {"prompt": f"{TRIGGER} {scene}", "guidance_scale": 7.5}
    if fast:
        inputs["model"] = "schnell"
        inputs["num_inference_steps"] = 4
    else:
        inputs["model"] = "dev"
        inputs["num_inference_steps"] = 28

    output = replicate.run(MODEL_ID, input=inputs)
    return str(output[0])  # Replicate returns a list of image URLs


if __name__ == "__main__":
    image_url = generate_image("black dog in a clean vector icon style, favicon, white background")
    print("Image:", image_url)
    if "--post" not in sys.argv:
        sys.exit("Not posted. Run with --post to publish it publicly to Mastodon.")

    media_id = upload_media_from_url(image_url, alt_text="Vector icon of a black dog (favicon style)")
    response = post_status("Testing my fine-tuned model 🔥", visibility="public", media_ids=[media_id])
    print("Posted:", response.get("url"))
