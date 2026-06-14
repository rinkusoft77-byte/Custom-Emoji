import asyncio
import json
import logging
import os
import sys
from html import escape
from pathlib import Path
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware, Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import MessageEntityType, ParseMode
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramRetryAfter,
)
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, MessageEntity, TelegramObject

router = Router()

USERS_FILE = Path(os.getenv("USERS_FILE", "data/users.json"))
USERS: set[int] = set()
USERS_LOCK = asyncio.Lock()


def parse_admin_ids(value: str) -> set[int]:
    admin_ids: set[int] = set()

    for item in value.replace(",", " ").split():
        try:
            admin_ids.add(int(item))
        except ValueError:
            logging.warning("Noto‘g‘ri ADMIN_IDS qiymati e’tiborsiz qoldirildi: %s", item)

    return admin_ids


ADMIN_IDS = parse_admin_ids(os.getenv("ADMIN_IDS", ""))


def load_users() -> None:
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)

    if not USERS_FILE.exists():
        return

    try:
        saved_users = json.loads(USERS_FILE.read_text(encoding="utf-8"))
        USERS.update(int(user_id) for user_id in saved_users)
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        logging.exception("Foydalanuvchilar faylini o‘qib bo‘lmadi.")


def write_users_file() -> None:
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary_file = USERS_FILE.with_suffix(".tmp")
    temporary_file.write_text(
        json.dumps(sorted(USERS), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary_file.replace(USERS_FILE)


async def add_user(user_id: int) -> None:
    async with USERS_LOCK:
        if user_id in USERS:
            return

        USERS.add(user_id)
        await asyncio.to_thread(write_users_file)


async def remove_users(user_ids: set[int]) -> None:
    if not user_ids:
        return

    async with USERS_LOCK:
        USERS.difference_update(user_ids)
        await asyncio.to_thread(write_users_file)


class RegisterUserMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if (
            isinstance(event, Message)
            and event.from_user
            and not event.from_user.is_bot
        ):
            await add_user(event.from_user.id)

        return await handler(event, data)


router.message.outer_middleware(RegisterUserMiddleware())


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


@router.message(Command("sendall"))
async def sendall_handler(message: Message, bot: Bot) -> None:
    if not message.from_user or message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔️ Bu komanda faqat admin uchun.")
        return

    command_text = message.text or message.caption or ""
    parts = command_text.split(maxsplit=1)
    broadcast_text = parts[1].strip() if len(parts) == 2 else ""

    if not message.reply_to_message and not broadcast_text:
        await message.answer(
            "📢 <b>Foydalanish:</b>\n\n"
            "<code>/sendall Xabaringiz</code>\n\n"
            "Yoki istalgan matn, rasm, video yoki boshqa xabarga reply qilib "
            "<code>/sendall</code> yozing."
        )
        return

    user_ids = list(USERS)
    if not user_ids:
        await message.answer("Foydalanuvchilar ro‘yxati bo‘sh.")
        return

    status_message = await message.answer(
        f"📤 Tarqatish boshlandi.\nJami foydalanuvchi: <b>{len(user_ids)}</b>"
    )

    sent = 0
    failed = 0
    blocked_users: set[int] = set()

    for user_id in user_ids:
        try:
            if message.reply_to_message:
                await message.reply_to_message.copy_to(chat_id=user_id)
            else:
                await bot.send_message(
                    chat_id=user_id,
                    text=broadcast_text,
                    parse_mode=None,
                )

            sent += 1
            await asyncio.sleep(0.05)

        except TelegramRetryAfter as error:
            await asyncio.sleep(error.retry_after)
            try:
                if message.reply_to_message:
                    await message.reply_to_message.copy_to(chat_id=user_id)
                else:
                    await bot.send_message(
                        chat_id=user_id,
                        text=broadcast_text,
                        parse_mode=None,
                    )
                sent += 1
            except TelegramForbiddenError:
                failed += 1
                blocked_users.add(user_id)
            except (TelegramBadRequest, TelegramRetryAfter):
                failed += 1

        except TelegramForbiddenError:
            failed += 1
            blocked_users.add(user_id)

        except TelegramBadRequest:
            failed += 1

        except Exception:
            failed += 1
            logging.exception("Xabarni %s foydalanuvchiga yuborib bo‘lmadi.", user_id)

    await remove_users(blocked_users)

    await status_message.edit_text(
        "✅ <b>Tarqatish yakunlandi!</b>\n\n"
        f"📨 Yuborildi: <b>{sent}</b>\n"
        f"❌ Yuborilmadi: <b>{failed}</b>\n"
        f"🚫 Bloklaganlar o‘chirildi: <b>{len(blocked_users)}</b>"
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

    if not ADMIN_IDS:
        logging.warning(
            "ADMIN_IDS kiritilmagan. /sendall komandasi hech kim uchun ishlamaydi."
        )

    load_users()

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
