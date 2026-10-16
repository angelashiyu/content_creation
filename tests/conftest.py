import os

# Several modules read credentials at import time. Dummy values let the tests import them
# without a .env; load_dotenv never overrides a variable that is already set, so real
# tokens are never used and no test reaches a network service.
for name in ("MASTODON_BASE_URL", "MASTODON_ACCESS_TOKEN", "OPENROUTER_API_KEY", "NOTION_TOKEN"):
    os.environ[name] = "https://test.invalid" if name == "MASTODON_BASE_URL" else "test"
