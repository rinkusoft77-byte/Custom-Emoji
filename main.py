import asyncio
import logging
import os
import sys
from html import escape

from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import MessageEntityType, ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, MessageEntity

router = Router()


def collect_custom_emoji_ids(message: Message) -> list[str]:
    """Return unique custom emoji IDs from message text or media caption."""
    entities: list[MessageEntity] = [
        *(message.entities or []),
        *(message.caption_entities or []),
    ]

    emoji_ids: list[str] = []
    seen: set[str] = set()

    for entity in entities:
        if (
            entity.type == MessageEntityType.CUSTOM_EMOJI
            and entity.custom_emoji_id
            and entity.custom_emoji_id not in seen
        ):
            emoji_ids.append(entity.custom_emoji_id)
            seen.add(entity.custom_emoji_id)

    return emoji_ids


@router.message(CommandStart())
async def start_handler(message: Message) -> None:
    await message.answer(
        "👋 <b>Custom Emoji ID Bot</b>\n\n"
        "Telegram Premium custom emojisini menga oddiy xabar yoki rasm captionida "
        "yuboring. Men uning <code>custom_emoji_id</code> qiymatini chiqaraman.\n\n"
        "Bir xabarda bir nechta custom emoji ham yuborishingiz mumkin."
    )


@router.message(Command("help"))
async def help_handler(message: Message) -> None:
    await message.answer(
        "<b>Qanday ishlatiladi?</b>\n\n"
        "1. Kerakli Premium emojini tanlang.\n"
        "2. Uni botga oddiy matn sifatida yuboring.\n"
        "3. Bot sizga emoji ID va tayyor HTML kodni beradi.\n\n"
        "Eslatma: oddiy Unicode emoji custom emoji hisoblanmaydi."
    )


@router.message()
async def custom_emoji_handler(message: Message) -> None:
    emoji_ids = collect_custom_emoji_ids(message)

    if not emoji_ids:
        await message.answer(
            "❌ <b>Custom emoji topilmadi.</b>\n\n"
            "Telegram Premium emojisini matn ichida yuboring. Oddiy emoji ID ga ega emas."
        )
        return

    sections: list[str] = []
    for index, emoji_id in enumerate(emoji_ids, start=1):
        html_example = f'<tg-emoji emoji-id="{emoji_id}">💎</tg-emoji>'
        sections.append(
            f"<b>{index}. Custom Emoji ID</b>\n"
            f"<code>{emoji_id}</code>\n\n"
            f"<b>HTML kodi:</b>\n"
            f"<code>{escape(html_example)}</code>"
        )

    await message.answer(
        "✅ <b>Topildi!</b>\n\n" + "\n\n──────────\n\n".join(sections)
    )


async def main() -> None:
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError(
            "BOT_TOKEN topilmadi. Environment variable sifatida bot tokenini kiriting."
        )

    bot = Bot(
        token=token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dispatcher = Dispatcher()
    dispatcher.include_router(router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dispatcher.start_polling(
        bot,
        allowed_updates=dispatcher.resolve_used_update_types(),
    )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stdout,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    asyncio.run(main())
