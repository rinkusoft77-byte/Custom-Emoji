import asyncio
import json
import logging
import os
import sys
from html import escape
from pathlib import Path
from time import monotonic
from typing import Any, Awaitable, Callable, Iterable

from aiogram import BaseMiddleware, Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import MessageEntityType, ParseMode
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramRetryAfter,
)
from aiogram.filters import Command, CommandStart
from aiogram.types import BotCommand, Message, MessageEntity, TelegramObject

router = Router()

USERS_FILE = Path(os.getenv("USERS_FILE", "data/users.json"))
USERS: set[int] = set()
USERS_LOCK = asyncio.Lock()
STARTED_AT = monotonic()


def parse_admin_ids(value: str) -> set[int]:
    admin_ids: set[int] = set()

    for item in value.replace(",", " ").split():
        try:
            admin_ids.add(int(item))
        except ValueError:
            logging.warning(
                "Noto‘g‘ri admin ID e’tiborsiz qoldirildi: %s. "
                "Username emas, raqamli Telegram ID kiriting.",
                item,
            )

    return admin_ids


def parse_nonnegative_float(name: str, default: float) -> float:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    try:
        value = float(raw_value)
    except ValueError:
        logging.warning("%s noto‘g‘ri: %r. Default %.3f ishlatiladi.", name, raw_value, default)
        return default

    if value < 0:
        logging.warning("%s manfiy bo‘lishi mumkin emas. Default %.3f ishlatiladi.", name, default)
        return default

    return value


def parse_positive_int(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    try:
        value = int(raw_value)
    except ValueError:
        logging.warning("%s noto‘g‘ri: %r. Default %s ishlatiladi.", name, raw_value, default)
        return default

    if value <= 0:
        logging.warning("%s 0 dan katta bo‘lishi kerak. Default %s ishlatiladi.", name, default)
        return default

    return value


ADMIN_IDS = parse_admin_ids(
    f'{os.getenv("ADMIN_IDS", "")} {os.getenv("ADMIN_ID", "")}'
)
BROADCAST_DELAY = parse_nonnegative_float("BROADCAST_DELAY", 0.05)
BROADCAST_PROGRESS_EVERY = parse_positive_int("BROADCAST_PROGRESS_EVERY", 25)


def is_admin(user_id: int | None) -> bool:
    return user_id is not None and user_id in ADMIN_IDS


def load_users() -> None:
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)

    if not USERS_FILE.exists():
        return

    try:
        saved_users = json.loads(USERS_FILE.read_text(encoding="utf-8"))
        if not isinstance(saved_users, list):
            raise ValueError("users.json list formatida bo‘lishi kerak")

        USERS.update(int(user_id) for user_id in saved_users)
        logging.info("%s ta foydalanuvchi yuklandi.", len(USERS))
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


def extract_custom_emoji_ids(entities: Iterable[MessageEntity]) -> list[str]:
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


def collect_custom_emoji_ids(message: Message) -> list[str]:
    """Return unique custom emoji IDs from message text or media caption."""
    entities: list[MessageEntity] = [
        *(message.entities or []),
        *(message.caption_entities or []),
    ]
    return extract_custom_emoji_ids(entities)


def format_uptime(seconds: float) -> str:
    total = max(0, int(seconds))
    days, remainder = divmod(total, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, secs = divmod(remainder, 60)

    parts: list[str] = []
    if days:
        parts.append(f"{days}d")
    if hours or days:
        parts.append(f"{hours}h")
    if minutes or hours or days:
        parts.append(f"{minutes}m")
    parts.append(f"{secs}s")
    return " ".join(parts)


async def set_bot_commands(bot: Bot) -> None:
    commands = [
        BotCommand(command="start", description="Botni ishga tushirish"),
        BotCommand(command="help", description="Qo‘llanma"),
        BotCommand(command="id", description="Telegram ID ni ko‘rish"),
        BotCommand(command="ping", description="Bot holatini tekshirish"),
    ]

    if ADMIN_IDS:
        commands.extend(
            [
                BotCommand(command="stats", description="Admin statistika"),
                BotCommand(command="sendall", description="Broadcast yuborish"),
            ]
        )

    await bot.set_my_commands(commands)


@router.message(CommandStart())
async def start_handler(message: Message) -> None:
    await message.answer(
        "👋 <b>Custom Emoji ID Bot v2</b>\n\n"
        "Telegram Premium custom emojisini menga oddiy xabar yoki media captionida "
        "yuboring. Men uning <code>custom_emoji_id</code> qiymatini chiqaraman.\n\n"
        "Bir xabarda bir nechta custom emoji yuborish mumkin.\n"
        "Yordam: <code>/help</code>"
    )


@router.message(Command("help"))
async def help_handler(message: Message) -> None:
    await message.answer(
        "<b>Qanday ishlatiladi?</b>\n\n"
        "1. Kerakli Premium emojini tanlang.\n"
        "2. Uni botga matn yoki media captionida yuboring.\n"
        "3. Bot emoji ID va tayyor HTML kodini beradi.\n\n"
        "<b>Komandalar:</b>\n"
        "• <code>/id</code> — Telegram ID\n"
        "• <code>/ping</code> — bot holati\n\n"
        "Eslatma: oddiy Unicode emoji custom emoji hisoblanmaydi."
    )


@router.message(Command("id"))
async def id_handler(message: Message) -> None:
    if not message.from_user:
        return

    admin_status = "✅ Admin" if is_admin(message.from_user.id) else "❌ Admin emas"

    await message.answer(
        "🆔 <b>Sizning Telegram ID’ingiz:</b>\n"
        f"<code>{message.from_user.id}</code>\n\n"
        f"<b>Botdagi holat:</b> {admin_status}\n\n"
        "Railway → Variables:\n"
        f"<code>ADMIN_IDS={message.from_user.id}</code>"
    )


@router.message(Command("ping"))
async def ping_handler(message: Message, bot: Bot) -> None:
    started = monotonic()
    me = await bot.get_me()
    latency_ms = (monotonic() - started) * 1000

    await message.answer(
        "🏓 <b>Pong!</b>\n\n"
        f"Bot: <b>@{escape(me.username or me.first_name)}</b>\n"
        f"API: <b>{latency_ms:.0f} ms</b>\n"
        f"Uptime: <b>{format_uptime(monotonic() - STARTED_AT)}</b>"
    )


@router.message(Command("stats"))
async def stats_handler(message: Message) -> None:
    if not message.from_user:
        return

    if not is_admin(message.from_user.id):
        await message.answer("⛔️ <b>Bu komanda faqat admin uchun.</b>")
        return

    await message.answer(
        "📊 <b>Bot statistikasi</b>\n\n"
        f"👥 Foydalanuvchilar: <b>{len(USERS)}</b>\n"
        f"👑 Adminlar: <b>{len(ADMIN_IDS)}</b>\n"
        f"⏱ Uptime: <b>{format_uptime(monotonic() - STARTED_AT)}</b>\n"
        f"💾 Storage: <code>{escape(str(USERS_FILE))}</code>\n"
        f"📨 Broadcast delay: <b>{BROADCAST_DELAY:.3f}s</b>"
    )


async def update_broadcast_status(
    status_message: Message,
    *,
    current: int,
    total: int,
    sent: int,
    failed: int,
) -> None:
    percent = (current / total * 100) if total else 100
    try:
        await status_message.edit_text(
            "📤 <b>Tarqatish davom etmoqda...</b>\n\n"
            f"Progress: <b>{current}/{total}</b> ({percent:.0f}%)\n"
            f"✅ Yuborildi: <b>{sent}</b>\n"
            f"❌ Xato: <b>{failed}</b>"
        )
    except TelegramBadRequest:
        pass


@router.message(Command("sendall"))
async def sendall_handler(message: Message, bot: Bot) -> None:
    if not message.from_user:
        return

    if not is_admin(message.from_user.id):
        await message.answer(
            "⛔️ <b>Bu komanda faqat admin uchun.</b>\n\n"
            f"Sizning ID’ingiz: <code>{message.from_user.id}</code>"
        )
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

    async def send_to_user(user_id: int) -> None:
        if message.reply_to_message:
            await message.reply_to_message.copy_to(chat_id=user_id)
        else:
            await bot.send_message(
                chat_id=user_id,
                text=broadcast_text,
                parse_mode=ParseMode.HTML,
            )

    for index, user_id in enumerate(user_ids, start=1):
        try:
            await send_to_user(user_id)
            sent += 1

        except TelegramRetryAfter as error:
            await asyncio.sleep(error.retry_after)
            try:
                await send_to_user(user_id)
                sent += 1
            except TelegramForbiddenError:
                failed += 1
                blocked_users.add(user_id)
            except (TelegramBadRequest, TelegramRetryAfter):
                failed += 1

        except TelegramForbiddenError:
            failed += 1
            blocked_users.add(user_id)

        except TelegramBadRequest as error:
            failed += 1
            logging.warning(
                "Xabarni %s foydalanuvchiga yuborib bo‘lmadi: %s",
                user_id,
                error,
            )

        except Exception:
            failed += 1
            logging.exception("Xabarni %s foydalanuvchiga yuborib bo‘lmadi.", user_id)

        if index % BROADCAST_PROGRESS_EVERY == 0 or index == len(user_ids):
            await update_broadcast_status(
                status_message,
                current=index,
                total=len(user_ids),
                sent=sent,
                failed=failed,
            )

        if BROADCAST_DELAY:
            await asyncio.sleep(BROADCAST_DELAY)

    await remove_users(blocked_users)

    await status_message.edit_text(
        "✅ <b>Tarqatish yakunlandi!</b>\n\n"
        f"📨 Yuborildi: <b>{sent}</b>\n"
        f"❌ Yuborilmadi: <b>{failed}</b>\n"
        f"🚫 Bloklaganlar o‘chirildi: <b>{len(blocked_users)}</b>\n"
        f"👥 Bazada qoldi: <b>{len(USERS)}</b>"
    )


async def get_emoji_metadata(
    bot: Bot,
    emoji_ids: list[str],
) -> dict[str, tuple[str | None, str | None]]:
    try:
        stickers = await bot.get_custom_emoji_stickers(custom_emoji_ids=emoji_ids)
    except (TelegramBadRequest, TelegramForbiddenError):
        logging.exception("Custom emoji metadata olishda Telegram API xatosi.")
        return {}
    except Exception:
        logging.exception("Custom emoji metadata olishda kutilmagan xato.")
        return {}

    metadata: dict[str, tuple[str | None, str | None]] = {}
    for sticker in stickers:
        if sticker.custom_emoji_id:
            metadata[sticker.custom_emoji_id] = (sticker.emoji, sticker.set_name)
    return metadata


@router.message()
async def custom_emoji_handler(message: Message, bot: Bot) -> None:
    emoji_ids = collect_custom_emoji_ids(message)

    if not emoji_ids:
        await message.answer(
            "❌ <b>Custom emoji topilmadi.</b>\n\n"
            "Telegram Premium emojisini matn yoki caption ichida yuboring. "
            "Oddiy Unicode emoji ID ga ega emas."
        )
        return

    metadata = await get_emoji_metadata(bot, emoji_ids)
    sections: list[str] = []

    for index, emoji_id in enumerate(emoji_ids, start=1):
        html_example = f'<tg-emoji emoji-id="{emoji_id}">💎</tg-emoji>'
        emoji_char, set_name = metadata.get(emoji_id, (None, None))

        extra_lines: list[str] = []
        if emoji_char:
            extra_lines.append(f"<b>Emoji:</b> {escape(emoji_char)}")
        if set_name:
            extra_lines.append(f"<b>Set:</b> <code>{escape(set_name)}</code>")

        extra = ("\n" + "\n".join(extra_lines)) if extra_lines else ""
        sections.append(
            f"<b>{index}. Custom Emoji ID</b>\n"
            f"<code>{emoji_id}</code>{extra}\n\n"
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
            "ADMIN_IDS yoki ADMIN_ID kiritilmagan. "
            "/stats va /sendall komandasi hech kim uchun ishlamaydi."
        )
    else:
        logging.info("Admin ID lar yuklandi: %s", sorted(ADMIN_IDS))

    load_users()

    bot = Bot(
        token=token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dispatcher = Dispatcher()
    dispatcher.include_router(router)

    await bot.delete_webhook(drop_pending_updates=True)
    await set_bot_commands(bot)

    bot_info = await bot.get_me()
    logging.info("Bot ishga tushdi: @%s (%s)", bot_info.username, bot_info.id)

    await dispatcher.start_polling(
        bot,
        allowed_updates=dispatcher.resolve_used_update_types(),
    )


if __name__ == "__main__":
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        stream=sys.stdout,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    asyncio.run(main())
