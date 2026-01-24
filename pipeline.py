import os
import asyncio
from approval_bot import ApprovalBot
from mastodon_publisher import publish_to_mastodon
from notion_fetch import get_context_text
from post_generator import generate_post as llm_generate_post
from chunking import chunk_document
from retrieval import retrieve_top_k


async def generate_post() -> str:
    context = get_context_text()
    chunks = chunk_document(context, mode="paragraph", target_chars=500)

    # Step 4: RAG retrieval
    query = "GenAI marketing intelligence platform AI answer visibility AI SEO"
    top_chunks = retrieve_top_k(query, chunks, k=6)

    context_for_llm = "\n\n---\n\n".join(top_chunks)

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
                await publish_to_mastodon(post)
                print("✅ Published to Mastodon.")
        elif decision == "reject":
            print(f"❌ Rejected. Reason: {reason}")
        else:
            print("⏳ Timed out waiting for approval.")
    finally:
        await approval.stop()

asyncio.run(main())