import logging
import os

from telegram import Bot
from telegram.error import TelegramError

from app.domain.models import ReportPayload

logger = logging.getLogger(__name__)


class TelegramService:
    def __init__(self, bot_token: str, chat_id: str) -> None:
        self.bot = Bot(token=bot_token)
        self.chat_id = chat_id

    async def send_report(self, payload: ReportPayload) -> None:
        image_path = payload.image_path
        try:
            if image_path:
                with open(image_path, "rb") as photo:
                    await self.bot.send_photo(
                        chat_id=self.chat_id,
                        photo=photo,
                        caption=payload.text,
                    )
            else:
                await self.bot.send_message(
                    chat_id=self.chat_id,
                    text=payload.text,
                )
            logger.info("Report sent to %s", self.chat_id)
        except TelegramError as exc:
            logger.error("Failed to send report to %s: %s", self.chat_id, exc)
            raise
        finally:
            if image_path:
                try:
                    os.unlink(image_path)
                except OSError:
                    logger.warning("Failed to remove temp map file: %s", image_path)
