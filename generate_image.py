import os
from dotenv import load_dotenv
import replicate

load_dotenv()

MODEL_ID = "sundai-club/ai_seo_promo_pics:0dfeb4c2070249fcb7306f098fa13cdc2a3fd35eff48d5b05f7988b4621f53d0"
TRIGGER_WORD = "ANGZIKI9"

def main():
    prompt = f"photo of {TRIGGER_WORD} in a space shuttle, realistic, high detail"

    # Option A: run the model (Replicate will use the latest version)
    output = replicate.run(
        MODEL_ID,
        input={
            "prompt": prompt,
            "model": "dev",                 # or "schnell" for speed
            "guidance_scale": 7.5,
            "num_inference_steps": 28,      # dev ~28-30; schnell use 4
        },
    )

    # output is usually a list of image URLs
    print("Output:", output)
    if isinstance(output, list) and output:
        print("First image URL:", output[0])

if __name__ == "__main__":
    main()
