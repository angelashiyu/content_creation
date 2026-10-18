import os
import uuid
import asyncio
from dataclasses import dataclass
from typing import Optional, Dict, Tuple
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

load_dotenv()

CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
REASON_TIMEOUT_S = 120  # after Reject, how long to wait for an optional reason

@dataclass
class Pending:
    post_text: str
    future: asyncio.Future  # resolves to Tuple[str, Optional[str]]
    chat_id: Optional[int] = None  # chat the request was sent to; only it may answer
    awaiting_reason: bool = False

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
        self.app.add_error_handler(self._on_error)

    async def start(self) -> None:
        await self.app.initialize()
        await self.app.start()
        # skip button taps and messages queued while no run was listening
        await self.app.updater.start_polling(drop_pending_updates=True)

    async def stop(self) -> None:
        await self.app.updater.stop()
        await self.app.stop()
        await self.app.shutdown()

    async def notify(self, text: str) -> None:
        await self.app.bot.send_message(chat_id=CHAT_ID, text=text)

    async def request_approval(self, post_text: str, timeout_s: int = 3600) -> Tuple[str, Optional[str]]:
        """
        Returns (decision, reason). decision in {"approve","reject","timeout"}
        """
        request_id = uuid.uuid4().hex[:10]
        loop = asyncio.get_running_loop()
        fut: asyncio.Future = loop.create_future()

        item = Pending(post_text=post_text, future=fut)
        self.pending[request_id] = item

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"approve:{request_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"reject:{request_id}"),
            ]
        ])

        message = await self.app.bot.send_message(
            chat_id=CHAT_ID,
            text=f"📝 New Post for Approval (id={request_id})\n\n{post_text}\n\nChars: {len(post_text)}",
            reply_markup=keyboard,
        )
        item.chat_id = message.chat_id

        try:
            return await asyncio.wait_for(fut, timeout=timeout_s)
        except asyncio.TimeoutError:
            # clean up
            self.pending.pop(request_id, None)
            # Reject was pressed but no reason arrived: still a rejection
            return ("reject", None) if item.awaiting_reason else ("timeout", None)

    def _resolve(self, request_id: str, decision: str, reason: Optional[str] = None) -> None:
        item = self.pending.pop(request_id, None)
        if item and not item.future.done():
            item.future.set_result((decision, reason))

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

        if not query.message or query.message.chat_id != item.chat_id:
            return

        if action == "approve":
            await query.edit_message_text(f"✅ APPROVED (id={request_id})\n\n{item.post_text}")
            self._resolve(request_id, "approve")
            return

        if action == "reject":
            item.awaiting_reason = True
            # the reason is optional: record the rejection without one if none arrives
            asyncio.get_running_loop().call_later(REASON_TIMEOUT_S, self._resolve, request_id, "reject")
            await query.edit_message_text(
                f"❌ REJECTED (id={request_id})\n\n"
                f"Reply in this chat within {REASON_TIMEOUT_S // 60} minutes to add a reason (optional)."
            )
            return

        await query.edit_message_text(f"Unknown action: {action}")

    async def _on_error(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        # one line instead of a traceback, e.g. for expired button taps
        print(f"Telegram handler error: {context.error}")

    async def _on_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message or not update.message.text:
            return

        # Find the first pending item from this chat that is awaiting a reason
        # (If you expect multiple simultaneous rejects, you can make this stricter.)
        for request_id, item in list(self.pending.items()):
            if item.awaiting_reason and item.chat_id == update.message.chat_id:
                reason = update.message.text.strip()
                await update.message.reply_text(f"📝 Feedback recorded for id={request_id}:\n\n{reason}")
                self._resolve(request_id, "reject", reason)
                return
