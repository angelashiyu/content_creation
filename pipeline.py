import os
import asyncio
from approval_bot import ApprovalBot
from mastodon_post import post_status
from notion_fetch import get_context_text
from post_generator import generate_post as llm_generate_post
from retrieval import build_context


async def generate_post() -> str:
    # Step 4: RAG retrieval
    context_for_llm = build_context(get_context_text())

    post = llm_generate_post(context_for_llm, topic="AI SEO", max_words=80)
    return post

async def main():
    approval = ApprovalBot()
    await approval.start()

    try:
        post = await generate_post()
        decision, reason = await approval.request_approval(post, timeout_s=1800)

        # ✅ add DRY_RUN logic here (right after decision)
        dry = os.environ.get("DRY_RUN", "false").lower() == "true"

        if decision == "approve":
            if dry:
                print("🧪 DRY_RUN: would publish this:\n", post)
            else:
                post_status(post)
                print("✅ Published to Mastodon.")
        elif decision == "reject":
            print(f"❌ Rejected. Reason: {reason}")
        else:
            print("⏳ Timed out waiting for approval.")
    finally:
        await approval.stop()

if __name__ == "__main__":
    asyncio.run(main())
