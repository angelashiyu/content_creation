import asyncio
import os
import uuid
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler, MessageHandler, filters

load_dotenv()

CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
REASON_WAIT_S = 120  # after Reject, how long to wait for an optional reason


class ApprovalBot:
    """Sends a draft to Telegram with Approve / Reject buttons and waits for the answer."""

    def __init__(self):
        self.app = Application.builder().token(BOT_TOKEN).build()
        self.app.add_handler(CallbackQueryHandler(self.on_button))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.on_text))
        self.app.add_error_handler(self.on_error)

        # the draft we are waiting on (only one at a time), or None
        self.pending = None

    async def start(self):
        await self.app.initialize()
        await self.app.start()
        # ignore button taps left over from earlier runs
        await self.app.updater.start_polling(drop_pending_updates=True)

    async def stop(self):
        await self.app.updater.stop()
        await self.app.stop()
        await self.app.shutdown()

    async def notify(self, text):
        await self.app.bot.send_message(chat_id=CHAT_ID, text=text)

    async def request_approval(self, post_text, timeout_s=3600):
        """Returns (decision, reason). decision is "approve", "reject" or "timeout"."""
        request_id = uuid.uuid4().hex[:10]
        self.pending = {
            "id": request_id,
            "text": post_text,
            "chat_id": None,
            "rejected": False,
            # a future is a box the button handler puts the answer into
            "answer": asyncio.get_running_loop().create_future(),
        }

        buttons = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Approve", callback_data=f"approve:{request_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"reject:{request_id}"),
        ]])
        message = await self.app.bot.send_message(
            chat_id=CHAT_ID,
            text=f"📝 New Post for Approval (id={request_id})\n\n{post_text}\n\nChars: {len(post_text)}",
            reply_markup=buttons,
        )
        self.pending["chat_id"] = message.chat_id  # only this chat may answer

        try:
            return await asyncio.wait_for(self.pending["answer"], timeout=timeout_s)
        except asyncio.TimeoutError:
            # Reject was pressed but no reason came in time: still a rejection
            if self.pending["rejected"]:
                return ("reject", None)
            return ("timeout", None)
        finally:
            self.pending = None

    def finish(self, request_id, decision, reason=None):
        pending = self.pending
        if pending and pending["id"] == request_id and not pending["answer"].done():
            pending["answer"].set_result((decision, reason))

    async def on_button(self, update, context):
        query = update.callback_query
        await query.answer()
        action, _, request_id = query.data.partition(":")  # "approve:abc123" -> "approve", "abc123"
        pending = self.pending

        if not pending or pending["id"] != request_id:
            await query.edit_message_text("This approval request is no longer active.")
            return
        if query.message.chat_id != pending["chat_id"]:
            return

        if action == "approve":
            await query.edit_message_text(f"✅ APPROVED (id={request_id})\n\n{pending['text']}")
            self.finish(request_id, "approve")
        elif action == "reject":
            pending["rejected"] = True
            # the reason is optional: if none arrives, record the rejection without one
            asyncio.get_running_loop().call_later(REASON_WAIT_S, self.finish, request_id, "reject")
            await query.edit_message_text(
                f"❌ REJECTED (id={request_id})\n\n"
                f"Reply in this chat within {REASON_WAIT_S // 60} minutes to add a reason (optional)."
            )

    async def on_text(self, update, context):
        # a text message after Reject is the reason
        message = update.message
        pending = self.pending
        if not message or not pending or not pending["rejected"] or message.chat_id != pending["chat_id"]:
            return

        reason = message.text.strip()
        await message.reply_text(f"📝 Feedback recorded for id={pending['id']}:\n\n{reason}")
        self.finish(pending["id"], "reject", reason)

    async def on_error(self, update, context):
        # one line instead of a long traceback, e.g. for expired button taps
        print(f"Telegram error: {context.error}")
