import os
# Example: pip install Mastodon.py
from mastodon import Mastodon

def get_client() -> Mastodon:
    return Mastodon(
        access_token=os.environ["MASTODON_ACCESS_TOKEN"],
        api_base_url=os.environ["MASTODON_BASE_URL"],  # e.g. "https://mastodon.social"
    )

async def publish_to_mastodon(text: str) -> None:
    client = get_client()
    # Mastodon.py is sync; call it directly or wrap in a thread if needed
    client.status_post(text)