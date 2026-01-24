import os
from mastodon import Mastodon

def get_client() -> Mastodon:
    return Mastodon(
        access_token=os.environ["MASTODON_ACCESS_TOKEN"],
        api_base_url=os.environ["MASTODON_BASE_URL"],
    )

async def publish_to_mastodon(text: str) -> None:
    client = get_client()
    client.status_post(text)