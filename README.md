# Custom Emoji ID Bot v2

Telegram Premium custom emojilarining `custom_emoji_id` qiymatini aniqlaydigan **Aiogram 3** bot.

## Imkoniyatlari

- Matn va media caption ichidagi custom emoji ID larini oladi
- Bir xabardagi bir nechta custom emoji ID ni chiqaradi
- Takrorlangan ID larni bir marta ko‘rsatadi
- Tayyor `<tg-emoji>` HTML kodini beradi
- Emoji metadata: emoji belgisi va sticker set nomini ko‘rsatishga harakat qiladi
- Foydalanuvchilarni avtomatik ro‘yxatga oladi
- Admin `/sendall` orqali barcha foydalanuvchilarga broadcast yubora oladi
- Broadcast progress holatini ko‘rsatadi
- Botni bloklagan foydalanuvchilarni bazadan avtomatik o‘chiradi
- Admin `/stats` orqali user count, uptime va storage holatini ko‘radi
- `/ping` orqali Telegram API javob vaqtini tekshiradi
- Telegram bot command menu avtomatik o‘rnatiladi
- Railway va Docker orqali deploy qilishga tayyor
- GitHub Actions CI orqali syntax va unit testlar tekshiriladi

## Talablar

- Python 3.10+
- Telegram bot tokeni
- `aiogram==3.28.2`

## Lokal ishga tushirish

```bash
git clone https://github.com/rinkusoft77-byte/Custom-Emoji.git
cd Custom-Emoji
python -m venv venv
```

Windows:

```powershell
venv\Scripts\activate
pip install -r requirements.txt
$env:BOT_TOKEN="BOTFATHER_DAN_OLINGAN_TOKEN"
$env:ADMIN_IDS="123456789"
python main.py
```

Linux/macOS:

```bash
source venv/bin/activate
pip install -r requirements.txt
export BOT_TOKEN="BOTFATHER_DAN_OLINGAN_TOKEN"
export ADMIN_IDS="123456789"
python main.py
```

## Environment variables

| Variable | Default | Vazifasi |
|---|---:|---|
| `BOT_TOKEN` | majburiy | BotFather tokeni |
| `ADMIN_IDS` | bo‘sh | Admin Telegram ID lar, vergul bilan ajratiladi |
| `ADMIN_ID` | bo‘sh | Bitta admin uchun backward-compatible alias |
| `USERS_FILE` | `data/users.json` | User storage fayli |
| `BROADCAST_DELAY` | `0.05` | Har bir broadcast xabar orasidagi kutish, sekund |
| `BROADCAST_PROGRESS_EVERY` | `25` | Nechta userdan keyin progress update qilinishi |
| `LOG_LEVEL` | `INFO` | Python logging darajasi |

Tayyor namuna `.env.example` faylida bor.

## Railway deploy

1. GitHub reponi Railway loyihasiga ulang.
2. `Variables` bo‘limida kamida quyidagilarni kiriting:

```text
BOT_TOKEN=BOTFATHER_DAN_OLINGAN_TOKEN
ADMIN_IDS=TELEGRAM_RAQAMLI_ID
```

3. Railway `Dockerfile` orqali botni ishga tushiradi.

### Foydalanuvchilarni doimiy saqlash

Redeploy yoki restart paytida user bazasi yo‘qolmasligi uchun Railway Volume ulang:

```text
USERS_FILE=/data/users.json
```

Volume mount path:

```text
/data
```

Bot eski `users.json` list formatini saqlab qoladi, shuning uchun v1 dan v2 ga o‘tishda migratsiya kerak emas.

## Komandalar

### `/start`
Botni ishga tushiradi va qisqa qo‘llanma beradi.

### `/help`
Custom emoji ID olish bo‘yicha qo‘llanma.

### `/id`
Foydalanuvchining Telegram numeric ID sini ko‘rsatadi.

### `/ping`
Telegram API javob vaqtini va bot uptime ni ko‘rsatadi.

### `/stats`
Faqat admin uchun:

- jami foydalanuvchilar
- adminlar soni
- uptime
- storage path
- broadcast delay

### `/sendall`
Faqat admin uchun.

Oddiy matn:

```text
/sendall Assalomu alaykum! Yangi yangilik bor.
```

Rasm, video, formatlangan matn yoki custom emoji yuborish uchun kerakli xabarga reply qilib:

```text
/sendall
```

Broadcast davomida progress ko‘rsatiladi. Botni bloklagan userlar avtomatik tozalanadi.

## Custom emoji ID olish

Botga Telegram Premium custom emojisini yuboring. Javob misoli:

```text
Custom Emoji ID:
5368324170671202286
```

HTML:

```html
<tg-emoji emoji-id="5368324170671202286">💎</tg-emoji>
```

## Test

```bash
python -m unittest discover -s tests -v
```

Syntax check:

```bash
python -m py_compile main.py
```

GitHub Actions har bir `main`/`upgrade/**` push va `main` ga ochilgan PR da ushbu tekshiruvlarni avtomatik bajaradi.

## Xavfsizlik

- Bot tokenini kod ichiga yozmang.
- `.env` faylini GitHub’ga push qilmang.
- `ADMIN_IDS` uchun username emas, numeric Telegram ID ishlating.
- Production’da `USERS_FILE` ni persistent volume ichida saqlang.
