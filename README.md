# Custom Emoji ID Bot

Telegram Premium custom emojilarining `custom_emoji_id` qiymatini aniqlaydigan Aiogram 3 bot.

## Imkoniyatlari

- Matndagi custom emoji ID larini oladi
- Media caption ichidagi custom emoji ID larini ham oladi
- Bir xabardagi bir nechta emoji ID ni chiqaradi
- Takrorlangan ID larni bir marta ko‘rsatadi
- Tayyor `<tg-emoji>` HTML kodini beradi
- Foydalanuvchilarni avtomatik ro‘yxatga oladi
- Admin `/sendall` orqali barcha foydalanuvchilarga xabar yubora oladi
- Matn, rasm, video va boshqa xabarlarni tarqatishni qo‘llab-quvvatlaydi
- Railway va Docker orqali ishga tushirishga tayyor

## Talablar

- Python 3.10 yoki undan yangi versiya
- Telegram bot tokeni
- `aiogram 3.28.2`

## Lokal ishga tushirish

### 1. Reponi klonlash

```bash
git clone https://github.com/rinkusoft77-byte/Custom-Emoji.git
cd Custom-Emoji
```

### 2. Virtual muhit yaratish

Windows:

```bash
python -m venv venv
venv\Scripts\activate
```

Linux/macOS:

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Kutubxonalarni o‘rnatish

```bash
pip install -r requirements.txt
```

### 4. Environment variables

Windows PowerShell:

```powershell
$env:BOT_TOKEN="BOTFATHER_DAN_OLINGAN_TOKEN"
$env:ADMIN_IDS="123456789"
python main.py
```

Windows CMD:

```cmd
set BOT_TOKEN=BOTFATHER_DAN_OLINGAN_TOKEN
set ADMIN_IDS=123456789
python main.py
```

Linux/macOS:

```bash
export BOT_TOKEN="BOTFATHER_DAN_OLINGAN_TOKEN"
export ADMIN_IDS="123456789"
python main.py
```

Bir nechta admin bo‘lsa, ID larni vergul bilan ajrating:

```text
ADMIN_IDS=123456789,987654321
```

## Railway orqali deploy

1. GitHub reponi Railway loyihasiga ulang.
2. `Variables` bo‘limiga kiring.
3. Quyidagi variable larni qo‘shing:

```text
BOT_TOKEN=BOTFATHER_DAN_OLINGAN_TOKEN
ADMIN_IDS=TELEGRAM_RAQAMLI_ID
```

4. Railway `Dockerfile` orqali botni avtomatik ishga tushiradi.

### Foydalanuvchilarni doimiy saqlash

Bot foydalanuvchilarni standart holatda `data/users.json` fayliga saqlaydi. Railway redeploy yoki restart paytida ma’lumot yo‘qolmasligi uchun Volume ulang va variable kiriting:

```text
USERS_FILE=/data/users.json
```

Volume mount path:

```text
/data
```

## Custom emoji ID olish

Botga Telegram Premium custom emojisini yuboring. Bot quyidagilarni qaytaradi:

```text
Custom Emoji ID:
5368324170671202286
```

HTML orqali ishlatish namunasi:

```html
<tg-emoji emoji-id="5368324170671202286">💎</tg-emoji>
```

## Barcha foydalanuvchilarga xabar yuborish

Oddiy matn yuborish:

```text
/sendall Assalomu alaykum! Yangi yangilik bor.
```

Rasm, video, formatlangan matn yoki custom emoji yuborish uchun kerakli xabarga reply qilib yozing:

```text
/sendall
```

Tarqatish tugagach, bot yuborilgan va yuborilmagan xabarlar sonini ko‘rsatadi. Botni bloklagan foydalanuvchilar bazadan avtomatik o‘chiriladi.

## Xavfsizlik

Bot tokenini kod ichiga yozmang va `.env` faylini GitHub’ga push qilmang. Token va admin ID faqat environment variable orqali beriladi.
