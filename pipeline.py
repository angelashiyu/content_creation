import os
import asyncio
from approval_bot import ApprovalBot
from mastodon_post import post_status
from notion_fetch import get_context_text
from post_generator import NO_POST, generate_post as llm_generate_post
from retrieval import build_context

MAX_POST_CHARS = 500  # Mastodon's default status limit
MAX_ATTEMPTS = 3  # drafts to try before giving up on the length limit


def generate_post(topic: str = "AI SEO") -> str:
    context_for_llm = build_context(get_context_text(), query=topic)

    # 80 words can run past 500 characters; regenerate rather than approve a post Mastodon will refuse
    for _ in range(MAX_ATTEMPTS):
        post = llm_generate_post(context_for_llm, topic=topic, max_words=80)
        if post == NO_POST or len(post) <= MAX_POST_CHARS:
            return post
    raise RuntimeError(f"no draft under {MAX_POST_CHARS} characters after {MAX_ATTEMPTS} attempts")

async def main():
    approval = ApprovalBot()
    await approval.start()

    try:
        post = generate_post()
        if post == NO_POST:
            print("No post drafted: the company context does not cover this topic.")
            return
        decision, reason = await approval.request_approval(post, timeout_s=1800)

        # DRY_RUN=true prints instead of publishing
        dry = os.environ.get("DRY_RUN", "false").lower() == "true"

        if decision == "approve":
            if dry:
                print("DRY_RUN: would publish this:\n", post)
            else:
                post_status(post)
                print("Approved. Published to Mastodon.")
        elif decision == "reject":
            print(f"Rejected. Reason: {reason}")
        else:
            print("Timed out waiting for approval.")
    except Exception as e:
        # scheduled runs have no one watching the logs, so say so in Telegram
        try:
            await approval.notify(f"⚠️ Post pipeline failed: {type(e).__name__}: {str(e)[:300]}")
        except Exception as notify_error:  # Telegram itself may be what failed
            print(f"Could not send failure notice: {notify_error}")
        raise
    finally:
        await approval.stop()

if __name__ == "__main__":
    asyncio.run(main())
