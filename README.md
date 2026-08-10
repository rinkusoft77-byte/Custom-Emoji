# Custom Emoji Toolkit

Telegram custom emojilarini tahlil qiladigan Aiogram 3 bot.

## Custom Emoji imkoniyatlari

- Custom emoji yuborilganda `custom_emoji_id` ni aniqlaydi
- Bir xabardagi bir nechta custom emoji ID larini oladi
- Takrorlangan ID larni avtomatik olib tashlaydi
- Media caption va quoted text ichidagi custom emoji entity larini taniydi
- Custom emoji formatini ko‘rsatadi: Static / Animated / Video
- Base Unicode emoji ni ko‘rsatadi
- `needs_repainting` holatini ko‘rsatadi
- Width, height va file size ma’lumotlarini chiqaradi
- Emoji qaysi custom emoji pack ga tegishli ekanini topadi
- Pack uchun `t.me/addemoji/...` link beradi
- Tayyor HTML `<tg-emoji>` kodini beradi
- Tayyor MarkdownV2 `tg://emoji?id=...` kodini beradi
- Developer uchun `file_id`, `file_unique_id` va boshqa metadata ni JSON ko‘rinishida beradi
- Bir so‘rovda 200 tagacha custom emoji ID bilan ishlaydi

## Komandalar

### `/emoji`

Custom emoji ID bo‘yicha to‘liq ma’lumot oladi.

```text
/emoji 5368324170671202286
```

Bir nechta ID ham berish mumkin:

```text
/emoji 5368324170671202286 5312361253610475399
```

Yoki custom emoji bor xabarga reply qilib:

```text
/emoji
```

### `/scan`

Custom emoji bor xabarga reply qilib yuboriladi. Reply qilingan xabardagi barcha custom emoji larni tahlil qiladi.

```text
/scan
```

### `/pack`

Custom emoji qaysi pack ga tegishli ekanini ko‘rsatadi:

- Pack title
- Pack short name
- Pack ichidagi emoji soni
- Telegram pack link

```text
/pack 5368324170671202286
```

Yoki emoji bor xabarga reply qilib:

```text
/pack
```

### `/json`

Developer uchun custom emoji metadata beradi.

```text
/json 5368324170671202286
```

Natijada quyidagi kabi maydonlar chiqadi:

```json
{
  "custom_emoji_id": "5368324170671202286",
  "emoji": "👍",
  "set_name": "example_pack",
  "format": "Animated (.TGS)",
  "is_animated": true,
  "is_video": false,
  "needs_repainting": false,
  "width": 100,
  "height": 100,
  "file_size": 12345,
  "file_id": "...",
  "file_unique_id": "..."
}
```

Agar JSON Telegram xabari uchun juda katta bo‘lsa, bot avtomatik `.json` fayl yuboradi.

## Oddiy foydalanish

Botga shunchaki Telegram custom emoji yuboring. Bot avtomatik ravishda quyidagilarni qaytaradi:

```text
Custom Emoji ID
Base emoji
Format
Recolor
O‘lcham
File size
Pack
Pack link
HTML
MarkdownV2
tg://emoji link
```

HTML namunasi:

```html
<tg-emoji emoji-id="5368324170671202286">👍</tg-emoji>
```

MarkdownV2 namunasi:

```text
![👍](tg://emoji?id=5368324170671202286)
```

Custom emoji pack link namunasi:

```text
https://t.me/addemoji/PACK_SHORT_NAME
```

## Mavjud boshqa funksiyalar

Oldingi funksiyalar saqlanadi:

- `/id`
- Admin `/sendall`
- User storage
- Railway / Docker deploy

Ularga yangi aloqasiz feature qo‘shilmagan.

## Talablar

- Python 3.10+
- Telegram bot tokeni
- `aiogram==3.28.2`

## Environment variables

```text
BOT_TOKEN=BOTFATHER_DAN_OLINGAN_TOKEN
ADMIN_IDS=123456789
USERS_FILE=data/users.json
```

Bir nechta admin:

```text
ADMIN_IDS=123456789,987654321
```

## Railway

Railway `Variables`:

```text
BOT_TOKEN=BOTFATHER_DAN_OLINGAN_TOKEN
ADMIN_IDS=TELEGRAM_RAQAMLI_ID
```

Persistent user storage kerak bo‘lsa Volume mount path:

```text
/data
```

va variable:

```text
USERS_FILE=/data/users.json
```

## Xavfsizlik

Bot tokenini kodga yozmang. `.env` faylini GitHub ga push qilmang.
