# 🎙️ Telegram Voice Reminder Bot (O'zbekiston uchun)

Ovozli xabarlardan eslatmalar yaratuvchi Telegram bot. Google Cloud Speech-to-Text orqali transkripsiya. **O'zbek** va **rus** tillarini qo'llab-quvvatlaydi.

Телеграм бот для создания напоминаний из голосовых сообщений. Транскрипция через Google Cloud Speech-to-Text. Поддерживает **узбекский** и **русский** языки.

## Imkoniyatlar / Возможности

- **Ovozdan matn**: Eslatma yaratish uchun ovozli xabar yuboring
- **Ko'p tilli qo'llab-quvvatlash**: O'zbek 🇺🇿, Rus 🇷🇺 (avtomatik aniqlanadi)
- **Tabiiy til vaqtini tahlil qilish**: "ertaga soat 3 da", "2 soatdan keyin", "dushanba kuni"
- **Vaqt zonasi**: Toshkent vaqti (Asia/Tashkent) sukut bo'yicha
- **Bir nechta vazifalar**: Bir ovozli xabardan bir nechta eslatma yarating
- **Aqlli takroriy eslatmalar**: 1 soatdan keyin vazifa bajarilganmi so'raydi
- **Kechiktirish**: Bajarilmagan vazifalarni osonlik bilan qayta rejalashtirish
- **Bot qayta ishga tushishi**: Ishlamay qolgan eslatmalarni yuboradi
- **Cheklash**: Haddan tashqari so'rovlarni oldini olish
- **Doimiy saqlash**: SQLite ma'lumotlar bazasi

## Maxsus holatlar / Особые случаи

| Holat / Ситуация | Xatti-harakat / Поведение |
|----------|----------|
| Yomon audio sifati | Qayta yozishni so'raydi / Просит перезаписать |
| Ovoz juda qisqa | Uzunroq yozishni so'raydi / Просит записать длиннее |
| Noaniq vaqt | Aniq vaqtni so'raydi / Просит уточнить время |
| Bir xabarda ko'p vazifa | Har biri uchun alohida eslatma / Отдельные напоминания |
| Vaqt zonasi | UTC saqlaydi, Toshkent vaqtida ko'rsatadi |
| Bot qayta ishga tushishi | O'tkazib yuborilgan eslatmalarni yuboradi |
| Cheklash | Haddan tashqari so'rovlarni bloklaydi |
| API xatolar | Eksponensial orqaga qaytish bilan qayta urinadi |

## Talablar / Требования

- Python 3.10 yoki undan yuqori
- FFmpeg (audio konvertatsiya uchun)
- Telegram Bot Token ([@BotFather](https://t.me/botfather) dan)
- Google Cloud hisob va Speech-to-Text API ([Google Cloud Console](https://console.cloud.google.com/) dan)

## O'rnatish / Установка

### 1. Loyihani yuklab oling

```bash
cd reminder_bot
```

### 2. Virtual muhit yarating

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/macOS
python3 -m venv venv
source venv/bin/activate
```

### 3. Kutubxonalarni o'rnating

```bash
pip install -r requirements.txt
```

### 4. Muhit o'zgaruvchilarini sozlang

```bash
# Windows
copy .env.example .env

# Linux/macOS
cp .env.example .env
```

`.env` faylini tahrirlang:

```env
TELEGRAM_TOKEN=sizning_telegram_bot_tokeningiz
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json
```

### 5. API kalitlarini oling

#### Telegram Bot Token:
1. Telegram'da [@BotFather](https://t.me/botfather) ni toping
2. `/newbot` buyrug'ini yuboring
3. Bot nomini kiriting
4. Tokenni nusxalang

#### Google Cloud Speech-to-Text:
1. [Google Cloud Console](https://console.cloud.google.com/) ga o'ting
2. Yangi loyiha yarating yoki mavjudini tanlang
3. "APIs & Services" > "Enable APIs" > "Cloud Speech-to-Text API" ni yoqing
4. "IAM & Admin" > "Service Accounts" ga o'ting
5. Yangi service account yarating
6. JSON kalit faylini yuklab oling
7. Faylni loyiha papkasiga joylashtiring
8. `.env` faylida `GOOGLE_APPLICATION_CREDENTIALS` ni o'rnating

#### FFmpeg o'rnatish (audio konvertatsiya uchun):
```bash
# Windows (Chocolatey bilan)
choco install ffmpeg

# Linux (Ubuntu/Debian)
sudo apt install ffmpeg

# macOS (Homebrew bilan)
brew install ffmpeg
```

### 6. Botni ishga tushiring

```bash
python bot.py
```

Ko'rsatiladi:
```
2024-XX-XX XX:XX:XX - __main__ - INFO - Starting Voice Reminder Bot...
2024-XX-XX XX:XX:XX - __main__ - INFO - Database initialized
2024-XX-XX XX:XX:XX - scheduler - INFO - Scheduler set up successfully
2024-XX-XX XX:XX:XX - __main__ - INFO - Bot is starting...
```

## Foydalanish / Использование

### Eslatmalar yaratish

Botga ovozli xabar yuboring:

**O'zbek (Uzbek):**
- "Ertaga soat 3 da onaga qo'ng'iroq qil"
- "2 soatdan keyin dori ich"
- "Dushanba kuni soat 10 da hisobot topshir"
- "30 minutdan keyin oziq-ovqat sotib ol"

**Rus (Русский):**
- "Напомни позвонить маме завтра в 3 часа"
- "Принять лекарство через 2 часа"
- "Сдать отчёт в понедельник в 10 утра"

**Bir nechta vazifa / Несколько задач:**
- "Soat 3 da Jonnga qo'ng'iroq qil va soat 5 da Saraga email yubor"
- "Напомни: позвонить в банк в 2 часа, и ещё купить продукты в 6 вечера"

### Buyruqlar / Команды

| Buyruq | Tavsif / Описание |
|---------|-------------|
| `/start` | Xush kelibsiz xabari |
| `/help` | Batafsil yordam |
| `/list` | Eslatmalar ro'yxati |
| `/timezone` | Vaqt zonasini o'zgartirish |
| `/done [id]` | Vazifani bajarilgan deb belgilash |
| `/delete [id]` | Eslatmani o'chirish |
| `/cancel` | Joriy amalni bekor qilish |

### Takroriy eslatmalar

1. Belgilangan vaqtda eslatma keladi
2. 1 soatdan keyin bot so'raydi: "Vazifa bajarildimi?" / "Задача выполнена?"
3. **HA/ДА** deb javob bering → Vazifa bajarilgan
4. **YO'Q/НЕТ** deb javob bering → Qachon yana eslatishni tanlang

## Project Structure

```
reminder_bot/
├── bot.py              # Main entry point, handlers setup
├── config.py           # Configuration and environment variables
├── database.py         # SQLite operations, user preferences, rate limiting
├── handlers.py         # Telegram message handlers with multi-language support
├── scheduler.py        # Reminder scheduling and restart recovery
├── time_parser.py      # Natural language time parsing (EN/RU/UZ)
├── transcription.py    # OpenAI Whisper with retry and error handling
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variables template
└── README.md           # This file
```

## Database Schema

```sql
-- User preferences for timezone and language
CREATE TABLE user_preferences (
    user_id INTEGER PRIMARY KEY,
    timezone TEXT DEFAULT 'UTC',
    language TEXT DEFAULT 'en',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Reminders with UTC storage
CREATE TABLE reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    chat_id INTEGER NOT NULL,
    task_text TEXT NOT NULL,
    scheduled_time_utc TIMESTAMP NOT NULL,
    user_timezone TEXT DEFAULT 'UTC',
    status TEXT DEFAULT 'pending',  -- pending, done, snoozed
    follow_up_sent INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Rate limiting
CREATE TABLE rate_limits (
    user_id INTEGER NOT NULL,
    timestamp TIMESTAMP NOT NULL
);
```

## Configuration Options

You can customize these in `config.py` or via environment variables:

| Setting | Default | Description |
|---------|---------|-------------|
| `FOLLOW_UP_DELAY_SECONDS` | 3600 | Time before follow-up (1 hour) |
| `DEFAULT_SNOOZE_MINUTES` | 30 | Default snooze duration |
| `DATABASE_PATH` | reminders.db | SQLite database location |
| `RATE_LIMIT_MESSAGES` | 10 | Max messages per window |
| `RATE_LIMIT_WINDOW_SECONDS` | 60 | Rate limit window (1 minute) |
| `MIN_VOICE_DURATION_SECONDS` | 1 | Minimum voice message length |
| `MAX_VOICE_DURATION_SECONDS` | 300 | Maximum voice message length |
| `MAX_RETRIES` | 3 | API retry attempts |

## Troubleshooting

### "TELEGRAM_TOKEN environment variable is required"
Make sure you've created a `.env` file with your Telegram token.

### "OPENAI_API_KEY environment variable is required"
Add your OpenAI API key to the `.env` file.

### Voice transcription fails
- Check your OpenAI API key is valid
- Ensure you have credits in your OpenAI account
- Verify the voice message is clear and audible
- Try speaking more slowly and clearly

### Audio quality issues
The bot will suggest:
- Speaking more clearly and slowly
- Recording in a quieter environment
- Holding the phone closer

### Time parsing issues
Try being more explicit:
- Instead of "later" → "in 2 hours" / "через 2 часа"
- Instead of "soon" → "in 30 minutes" / "через 30 минут"
- Include specific times: "at 3pm", "at 15:00", "в 3 часа"

### Timezone issues
Set your timezone with `/timezone` command. Supported formats:
- City names: "Moscow", "Tashkent", "New York"
- IANA format: "Europe/Moscow", "Asia/Tashkent"

## Production Deployment

For production use, consider:

1. **Use a process manager** like `systemd` or `supervisor`
2. **Set up logging** to a persistent location
3. **Use environment-specific** `.env` files
4. **Back up the database** regularly
5. **Monitor API usage** on OpenAI dashboard

### Example systemd service (`/etc/systemd/system/reminder-bot.service`):

```ini
[Unit]
Description=Telegram Voice Reminder Bot
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/reminder_bot
Environment=PATH=/path/to/reminder_bot/venv/bin
ExecStart=/path/to/reminder_bot/venv/bin/python bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## License

MIT License - Feel free to use and modify as needed.

## Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.
