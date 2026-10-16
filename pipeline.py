import os
import asyncio
from approval_bot import ApprovalBot
from mastodon_post import post_status
from notion_fetch import get_context_text
from post_generator import NO_POST, generate_post as llm_generate_post
from retrieval import build_context


def generate_post(topic: str = "AI SEO") -> str:
    context_for_llm = build_context(get_context_text(), query=topic)

    post = llm_generate_post(context_for_llm, topic=topic, max_words=80)
    return post

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
    finally:
        await approval.stop()

if __name__ == "__main__":
    asyncio.run(main())
