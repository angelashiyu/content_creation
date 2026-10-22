import asyncio
import os
from approval_bot import ApprovalBot
from mastodon_post import post_status
from notion_fetch import get_context_text
from post_generator import NO_POST, generate_post
from retrieval import build_context

TOPIC = "AI SEO"
MAX_POST_CHARS = 500  # Mastodon's default limit
MAX_ATTEMPTS = 3
DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"  # true = print instead of publishing


def write_draft(topic):
    context = build_context(get_context_text(), query=topic)

    # 80 words can be more than 500 characters, so try again instead of sending a post Mastodon will refuse
    for attempt in range(MAX_ATTEMPTS):
        post = generate_post(context, topic=topic, max_words=80)
        if post == NO_POST or len(post) <= MAX_POST_CHARS:
            return post
    raise RuntimeError(f"no draft under {MAX_POST_CHARS} characters after {MAX_ATTEMPTS} tries")


async def main():
    bot = ApprovalBot()
    await bot.start()

    try:
        post = write_draft(TOPIC)
        if post == NO_POST:
            print("No post drafted: the company context does not cover this topic.")
            return

        decision, reason = await bot.request_approval(post, timeout_s=1800)

        if decision == "approve" and DRY_RUN:
            print("DRY_RUN: would publish this:\n", post)
        elif decision == "approve":
            post_status(post)
            print("Approved. Published to Mastodon.")
        elif decision == "reject":
            print(f"Rejected. Reason: {reason}")
        else:
            print("Timed out waiting for approval.")

    except Exception as e:
        # nobody watches the logs of a scheduled run, so send the error to Telegram too
        try:
            await bot.notify(f"⚠️ Post pipeline failed: {repr(e)}"[:400])
        except Exception as telegram_error:
            print(f"Could not send failure message: {telegram_error}")
        raise

    finally:
        await bot.stop()


if __name__ == "__main__":
    asyncio.run(main())
