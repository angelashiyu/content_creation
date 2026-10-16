"""Copy the pipeline's credentials from .env into SSM Parameter Store as SecureStrings."""
import subprocess
import sys
from pathlib import Path
from dotenv import dotenv_values

PREFIX = "/genai-post"
NAMES = [
    "MASTODON_BASE_URL",
    "MASTODON_ACCESS_TOKEN",
    "OPENROUTER_API_KEY",
    "NOTION_TOKEN",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
]

def main():
    env = dotenv_values(Path(__file__).resolve().parent.parent / ".env")
    missing = [n for n in NAMES if not env.get(n)]
    if missing:
        sys.exit(f"Missing from .env: {', '.join(missing)}")

    for name in NAMES:
        subprocess.run(
            ["aws", "ssm", "put-parameter", "--name", f"{PREFIX}/{name}",
             "--type", "SecureString", "--value", env[name], "--overwrite"],
            check=True, stdout=subprocess.DEVNULL,
        )
        print(f"stored {PREFIX}/{name}")

if __name__ == "__main__":
    main()
