import asyncio
import json
import logging
import os
import re
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
from aiogram.types import BufferedInputFile, Message, MessageEntity, Sticker, StickerSet, TelegramObject

router = Router()

USERS_FILE = Path(os.getenv("USERS_FILE", "data/users.json"))
USERS: set[int] = set()
USERS_LOCK = asyncio.Lock()
MAX_EMOJI_IDS = 200
MAX_MESSAGE_LENGTH = 3900


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


ADMIN_IDS = parse_admin_ids(
    f'{os.getenv("ADMIN_IDS", "")} {os.getenv("ADMIN_ID", "")}'
)


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
    """Return unique custom emoji IDs from message text, caption and quote."""
    entities: list[MessageEntity] = [
        *(message.entities or []),
        *(message.caption_entities or []),
    ]

    if message.quote and message.quote.entities:
        entities.extend(message.quote.entities)

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

    return emoji_ids[:MAX_EMOJI_IDS]


def parse_custom_emoji_ids(value: str) -> list[str]:
    """Parse unique numeric custom emoji IDs from arbitrary command text."""
    ids = re.findall(r"\d{10,25}", value)
    return list(dict.fromkeys(ids))[:MAX_EMOJI_IDS]


def sticker_format(sticker: Sticker) -> str:
    if sticker.is_animated:
        return "Animated (.TGS)"
    if sticker.is_video:
        return "Video (.WEBM)"
    return "Static (.WEBP/PNG)"


async def get_custom_emoji_map(bot: Bot, emoji_ids: list[str]) -> dict[str, Sticker]:
    if not emoji_ids:
        return {}

    try:
        stickers = await bot.get_custom_emoji_stickers(
            custom_emoji_ids=emoji_ids[:MAX_EMOJI_IDS]
        )
    except TelegramBadRequest:
        logging.exception("Custom emoji ma’lumotlarini olishda Telegram API xatosi.")
        return {}

    return {
        sticker.custom_emoji_id: sticker
        for sticker in stickers
        if sticker.custom_emoji_id
    }


async def get_sticker_sets(
    bot: Bot,
    stickers: list[Sticker],
) -> dict[str, StickerSet]:
    result: dict[str, StickerSet] = {}
    set_names = {
        sticker.set_name
        for sticker in stickers
        if sticker.set_name
    }

    for set_name in set_names:
        try:
            result[set_name] = await bot.get_sticker_set(name=set_name)
        except TelegramBadRequest:
            logging.warning("Sticker set topilmadi: %s", set_name)

    return result


def build_emoji_section(
    index: int,
    emoji_id: str,
    sticker: Sticker | None,
) -> str:
    if not sticker:
        return (
            f"<b>{index}. Custom Emoji</b>\n"
            f"🆔 <code>{emoji_id}</code>\n"
            "❌ Telegram bu ID uchun custom emoji topmadi."
        )

    base_emoji = sticker.emoji or "🙂"
    html_code = f'<tg-emoji emoji-id="{emoji_id}">{base_emoji}</tg-emoji>'
    markdown_code = f"![{base_emoji}](tg://emoji?id={emoji_id})"
    tg_link = f"tg://emoji?id={emoji_id}"

    lines = [
        f"<b>{index}. Custom Emoji</b>",
        f"🆔 <b>ID:</b> <code>{emoji_id}</code>",
        f"🙂 <b>Base emoji:</b> {escape(base_emoji)}",
        f"🎞 <b>Format:</b> {sticker_format(sticker)}",
        "🎨 <b>Recolor:</b> "
        + ("✅ Ha" if sticker.needs_repainting else "❌ Yo‘q"),
        f"📐 <b>O‘lcham:</b> {sticker.width}×{sticker.height}",
    ]

    if sticker.file_size is not None:
        lines.append(f"📦 <b>File size:</b> {sticker.file_size:,} byte")

    if sticker.set_name:
        lines.extend(
            [
                f"📚 <b>Pack:</b> <code>{escape(sticker.set_name)}</code>",
                f'🔗 <b>Pack link:</b> '
                f'<a href="https://t.me/addemoji/{escape(sticker.set_name)}">'
                "ochish</a>",
            ]
        )

    lines.extend(
        [
            "",
            "<b>HTML:</b>",
            f"<code>{escape(html_code)}</code>",
            "",
            "<b>MarkdownV2:</b>",
            f"<code>{escape(markdown_code)}</code>",
            "",
            "<b>tg link:</b>",
            f"<code>{escape(tg_link)}</code>",
        ]
    )

    return "\n".join(lines)


async def send_emoji_report(
    message: Message,
    bot: Bot,
    emoji_ids: list[str],
) -> None:
    emoji_ids = list(dict.fromkeys(emoji_ids))[:MAX_EMOJI_IDS]

    if not emoji_ids:
        await message.answer(
            "❌ <b>Custom emoji topilmadi.</b>\n\n"
            "Custom emoji yuboring, xabarga reply qilib <code>/scan</code> yozing "
            "yoki <code>/emoji ID</code> ishlating."
        )
        return

    emoji_map = await get_custom_emoji_map(bot, emoji_ids)
    sections = [
        build_emoji_section(
            index,
            emoji_id,
            emoji_map.get(emoji_id),
        )
        for index, emoji_id in enumerate(emoji_ids, start=1)
    ]

    chunks: list[str] = []
    current = "✅ <b>Custom Emoji ma’lumotlari</b>\n\n"

    for section in sections:
        candidate = current + section + "\n\n──────────\n\n"
        if len(candidate) > MAX_MESSAGE_LENGTH and current.strip():
            chunks.append(current.removesuffix("\n\n──────────\n\n"))
            current = section + "\n\n──────────\n\n"
        else:
            current = candidate

    if current.strip():
        chunks.append(current.removesuffix("\n\n──────────\n\n"))

    for chunk in chunks:
        await message.answer(
            chunk,
            disable_web_page_preview=True,
        )


def command_payload(message: Message) -> str:
    text = message.text or message.caption or ""
    parts = text.split(maxsplit=1)
    return parts[1] if len(parts) == 2 else ""


@router.message(CommandStart())
async def start_handler(message: Message) -> None:
    await message.answer(
        "👋 <b>Custom Emoji Toolkit</b>\n\n"
        "Custom emoji yuboring — bot ID, format, pack va tayyor kodlarni chiqaradi.\n\n"
        "🔎 <code>/emoji ID</code> — ID bo‘yicha tekshirish\n"
        "🧪 <code>/scan</code> — reply qilingan xabardagi emoji’larni skan qilish\n"
        "📚 <code>/pack ID</code> — emoji pack haqida ma’lumot\n"
        "🧾 <code>/json ID</code> — developer uchun JSON metadata"
    )


@router.message(Command("help"))
async def help_handler(message: Message) -> None:
    await message.answer(
        "<b>Custom Emoji funksiyalari</b>\n\n"
        "• Custom emoji yuboring — avtomatik to‘liq info\n"
        "• <code>/emoji 5368324170671202286</code> — ID’dan emoji info\n"
        "• Xabarga reply → <code>/scan</code> — ichidagi barcha custom emoji\n"
        "• <code>/pack ID</code> — pack nomi, soni va linki\n"
        "• <code>/json ID</code> — file_id va texnik metadata\n\n"
        "Bir komandada bir nechta ID berish mumkin. Maksimum 200 ta."
    )


@router.message(Command("id"))
async def id_handler(message: Message) -> None:
    if not message.from_user:
        return

    is_admin = message.from_user.id in ADMIN_IDS
    admin_status = "✅ Admin" if is_admin else "❌ Admin emas"

    await message.answer(
        "🆔 <b>Sizning Telegram ID’ingiz:</b>\n"
        f"<code>{message.from_user.id}</code>\n\n"
        f"<b>Botdagi holat:</b> {admin_status}\n\n"
        "Railway → Variables ichida quyidagicha yozing:\n"
        f"<code>ADMIN_IDS={message.from_user.id}</code>\n\n"
        "So‘ng Railway deployment’ni restart yoki redeploy qiling."
    )


@router.message(Command("emoji"))
async def emoji_by_id_handler(message: Message, bot: Bot) -> None:
    emoji_ids = parse_custom_emoji_ids(command_payload(message))

    if not emoji_ids and message.reply_to_message:
        emoji_ids = collect_custom_emoji_ids(message.reply_to_message)

    if not emoji_ids:
        await message.answer(
            "Foydalanish:\n"
            "<code>/emoji 5368324170671202286</code>\n\n"
            "Yoki custom emoji bor xabarga reply qilib <code>/emoji</code> yozing."
        )
        return

    await send_emoji_report(message, bot, emoji_ids)


@router.message(Command("scan"))
async def scan_handler(message: Message, bot: Bot) -> None:
    if not message.reply_to_message:
        await message.answer(
            "🔎 Custom emoji bor xabarga <b>reply</b> qilib "
            "<code>/scan</code> yozing."
        )
        return

    await send_emoji_report(
        message,
        bot,
        collect_custom_emoji_ids(message.reply_to_message),
    )


@router.message(Command("pack"))
async def pack_handler(message: Message, bot: Bot) -> None:
    emoji_ids = parse_custom_emoji_ids(command_payload(message))

    if not emoji_ids and message.reply_to_message:
        emoji_ids = collect_custom_emoji_ids(message.reply_to_message)

    if not emoji_ids:
        await message.answer(
            "📚 <code>/pack CUSTOM_EMOJI_ID</code>\n"
            "yoki custom emoji bor xabarga reply qilib <code>/pack</code> yozing."
        )
        return

    emoji_map = await get_custom_emoji_map(bot, emoji_ids)
    stickers = list(emoji_map.values())

    if not stickers:
        await message.answer("❌ Bu ID bo‘yicha custom emoji topilmadi.")
        return

    sticker_sets = await get_sticker_sets(bot, stickers)
    seen: set[str] = set()
    sections: list[str] = []

    for sticker in stickers:
        if not sticker.set_name or sticker.set_name in seen:
            continue

        seen.add(sticker.set_name)
        sticker_set = sticker_sets.get(sticker.set_name)
        title = sticker_set.title if sticker_set else sticker.set_name
        count = len(sticker_set.stickers) if sticker_set else "—"

        sections.append(
            "📚 <b>Custom Emoji Pack</b>\n"
            f"🏷 <b>Nomi:</b> {escape(title)}\n"
            f"🔑 <b>Short name:</b> <code>{escape(sticker.set_name)}</code>\n"
            f"🔢 <b>Emoji soni:</b> {count}\n"
            f'🔗 <a href="https://t.me/addemoji/{escape(sticker.set_name)}">'
            "Packni Telegram’da ochish</a>"
        )

    if not sections:
        await message.answer("❌ Emoji uchun sticker pack ma’lumoti topilmadi.")
        return

    await message.answer(
        "\n\n──────────\n\n".join(sections),
        disable_web_page_preview=True,
    )


@router.message(Command("json"))
async def json_handler(message: Message, bot: Bot) -> None:
    emoji_ids = parse_custom_emoji_ids(command_payload(message))

    if not emoji_ids and message.reply_to_message:
        emoji_ids = collect_custom_emoji_ids(message.reply_to_message)

    if not emoji_ids:
        await message.answer(
            "🧾 <code>/json CUSTOM_EMOJI_ID</code>\n"
            "yoki custom emoji bor xabarga reply qilib <code>/json</code> yozing."
        )
        return

    emoji_map = await get_custom_emoji_map(bot, emoji_ids)
    payload: list[dict[str, Any]] = []

    for emoji_id in emoji_ids:
        sticker = emoji_map.get(emoji_id)
        if not sticker:
            payload.append({"custom_emoji_id": emoji_id, "found": False})
            continue

        payload.append(
            {
                "custom_emoji_id": emoji_id,
                "found": True,
                "emoji": sticker.emoji,
                "set_name": sticker.set_name,
                "format": sticker_format(sticker),
                "is_animated": sticker.is_animated,
                "is_video": sticker.is_video,
                "needs_repainting": bool(sticker.needs_repainting),
                "width": sticker.width,
                "height": sticker.height,
                "file_size": sticker.file_size,
                "file_id": sticker.file_id,
                "file_unique_id": sticker.file_unique_id,
            }
        )

    json_text = json.dumps(payload, ensure_ascii=False, indent=2)

    if len(json_text) <= 3500:
        await message.answer(f"<pre>{escape(json_text)}</pre>")
        return

    document = BufferedInputFile(
        json_text.encode("utf-8"),
        filename="custom_emoji_metadata.json",
    )
    await message.answer_document(
        document=document,
        caption=f"🧾 {len(payload)} ta custom emoji metadata",
    )


@router.message(Command("sendall"))
async def sendall_handler(message: Message, bot: Bot) -> None:
    if not message.from_user:
        return

    if message.from_user.id not in ADMIN_IDS:
        await message.answer(
            "⛔️ <b>Bu komanda faqat admin uchun.</b>\n\n"
            f"Sizning ID’ingiz: <code>{message.from_user.id}</code>\n\n"
            "Railway → Variables ichida quyidagicha kiriting:\n"
            f"<code>ADMIN_IDS={message.from_user.id}</code>\n\n"
            "Keyin deployment’ni restart yoki redeploy qiling."
        )
        return

    command_text = message.text or message.caption or ""
    parts = command_text.split(maxsplit=1)
    broadcast_text = parts[1].strip() if len(parts) == 2 else ""

    if not message.reply_to_message and not broadcast_text:
        await message.answer(
            "📢 <b>Foydalanish:</b>\n\n"
            "<code>/sendall Xabaringiz</code>\n\n"
            "HTML custom emoji kodi ham ishlaydi:\n"
            '<code>/sendall &lt;tg-emoji emoji-id="5312361253610475399"&gt;'
            "💎&lt;/tg-emoji&gt;</code>\n\n"
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

    for user_id in user_ids:
        try:
            await send_to_user(user_id)
            sent += 1
            await asyncio.sleep(0.05)

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

    await remove_users(blocked_users)

    await status_message.edit_text(
        "✅ <b>Tarqatish yakunlandi!</b>\n\n"
        f"📨 Yuborildi: <b>{sent}</b>\n"
        f"❌ Yuborilmadi: <b>{failed}</b>\n"
        f"🚫 Bloklaganlar o‘chirildi: <b>{len(blocked_users)}</b>"
    )


@router.message()
async def custom_emoji_handler(message: Message, bot: Bot) -> None:
    emoji_ids = collect_custom_emoji_ids(message)

    if not emoji_ids:
        await message.answer(
            "❌ <b>Custom emoji topilmadi.</b>\n\n"
            "Telegram Premium custom emojisini yuboring.\n"
            "ID bo‘lsa: <code>/emoji ID</code>"
        )
        return

    await send_emoji_report(message, bot, emoji_ids)


async def main() -> None:
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError(
            "BOT_TOKEN topilmadi. Environment variable sifatida bot tokenini kiriting."
        )

    if not ADMIN_IDS:
        logging.warning(
            "ADMIN_IDS yoki ADMIN_ID kiritilmagan. "
            "/sendall komandasi hech kim uchun ishlamaydi."
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
