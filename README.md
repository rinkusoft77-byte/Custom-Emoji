# Custom Emoji ID Bot

Telegram Premium custom emojilarining `custom_emoji_id` qiymatini aniqlaydigan Aiogram 3 bot.

## Imkoniyatlari

- Matndagi custom emoji ID larini oladi
- Media caption ichidagi custom emoji ID larini ham oladi
- Bir xabardagi bir nechta emoji ID ni chiqaradi
- Takrorlangan ID larni bir marta ko‘rsatadi
- Tayyor `<tg-emoji>` HTML kodini beradi
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

### 4. Bot tokenini kiritish

Windows PowerShell:

```powershell
$env:BOT_TOKEN="BOTFATHER_DAN_OLINGAN_TOKEN"
python main.py
```

Windows CMD:

```cmd
set BOT_TOKEN=BOTFATHER_DAN_OLINGAN_TOKEN
python main.py
```

Linux/macOS:

```bash
export BOT_TOKEN="BOTFATHER_DAN_OLINGAN_TOKEN"
python main.py
```

## Railway orqali deploy

1. GitHub reponi Railway loyihasiga ulang.
2. `Variables` bo‘limiga kiring.
3. Quyidagi variable ni qo‘shing:

```text
BOT_TOKEN=BOTFATHER_DAN_OLINGAN_TOKEN
```

4. Railway `Dockerfile` orqali botni avtomatik ishga tushiradi.

## Ishlatish

Botga Telegram Premium custom emojisini yuboring. Bot quyidagilarni qaytaradi:

```text
Custom Emoji ID:
5368324170671202286
```

HTML orqali ishlatish namunasi:

```html
<tg-emoji emoji-id="5368324170671202286">💎</tg-emoji>
```

## Xavfsizlik

Bot tokenini kod ichiga yozmang va `.env` faylini GitHub’ga push qilmang. Token faqat environment variable orqali beriladi.
