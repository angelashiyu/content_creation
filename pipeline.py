import asyncio
from approval_bot import ApprovalBot
from mastodon_publisher import publish_to_mastodon

async def generate_post() -> str:
    # Replace with your real generation logic
    return "🚀 Draft post...\n\nDo we ship this?"

async def main():
    approval = ApprovalBot()
    await approval.start()

    try:
        post = await generate_post()

        decision, reason = await approval.request_approval(post, timeout_s=1800)

        if decision == "approve":
            await publish_to_mastodon(post)
            print("✅ Published to Mastodon.")
        elif decision == "reject":
            print(f"❌ Rejected. Reason: {reason}")
            # Optional: regenerate using reason and repeat
        else:
            print("⏳ Timed out waiting for approval.")
    finally:
        await approval.stop()

asyncio.run(main())