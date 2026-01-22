import os
import uuid
import asyncio
from dataclasses import dataclass
from typing import Optional, Dict, Tuple
from dotenv import load_dotenv
load_dotenv()


from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

@dataclass
class Pending:
    post_text: str
    future: asyncio.Future  # resolves to Tuple[str, Optional[str]]
    awaiting_reason: bool = False
    reject_message_chat_id: Optional[int] = None  # who to listen to for reason

class ApprovalBot:
    """
    Long-lived Telegram bot that can:
      - send approval requests (with buttons)
      - wait for approval/rejection (+ optional reject reason)
    """

    def __init__(self) -> None:
        self.app = Application.builder().token(BOT_TOKEN).build()
        self.pending: Dict[str, Pending] = {}

        self.app.add_handler(CallbackQueryHandler(self._on_button))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._on_text))

    async def start(self) -> None:
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()

    async def stop(self) -> None:
        await self.app.updater.stop()
        await self.app.stop()
        await self.app.shutdown()

    async def request_approval(self, post_text: str, timeout_s: int = 3600) -> Tuple[str, Optional[str]]:
        """
        Returns (decision, reason). decision in {"approve","reject","timeout"}
        """
        request_id = uuid.uuid4().hex[:10]
        loop = asyncio.get_running_loop()
        fut: asyncio.Future = loop.create_future()

        self.pending[request_id] = Pending(post_text=post_text, future=fut)

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"approve:{request_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"reject:{request_id}"),
            ]
        ])

        await self.app.bot.send_message(
            chat_id=CHAT_ID,
            text=f"📝 New Post for Approval (id={request_id})\n\n{post_text}\n\nChars: {len(post_text)}",
            reply_markup=keyboard,
        )

        try:
            return await asyncio.wait_for(fut, timeout=timeout_s)
        except asyncio.TimeoutError:
            # clean up
            self.pending.pop(request_id, None)
            return ("timeout", None)

    async def _on_button(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        if not query or not query.data:
            return

        await query.answer()

        try:
            action, request_id = query.data.split(":", 1)
        except ValueError:
            await query.edit_message_text("Malformed callback data.")
            return

        item = self.pending.get(request_id)
        if not item:
            await query.edit_message_text("This approval request is no longer active.")
            return

        if action == "approve":
            await query.edit_message_text(f"✅ APPROVED (id={request_id})\n\n{item.post_text}")
            if not item.future.done():
                item.future.set_result(("approve", None))
            self.pending.pop(request_id, None)
            return

        if action == "reject":
            item.awaiting_reason = True
            item.reject_message_chat_id = query.message.chat_id if query.message else None
            await query.edit_message_text(
                f"❌ REJECTED (id={request_id})\n\n"
                f"Reply in this chat with the reason for rejection."
            )
            return

        await query.edit_message_text(f"Unknown action: {action}")

    async def _on_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message or not update.message.text:
            return

        # Find the first pending item that is awaiting a reason
        # (If you expect multiple simultaneous rejects, you can make this stricter.)
        for request_id, item in list(self.pending.items()):
            if item.awaiting_reason:
                reason = update.message.text.strip()
                await update.message.reply_text(f"📝 Feedback recorded for id={request_id}:\n\n{reason}")

                if not item.future.done():
                    item.future.set_result(("reject", reason))
                self.pending.pop(request_id, None)
                return