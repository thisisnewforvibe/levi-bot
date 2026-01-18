"""
Telegram bot handlers for all commands and messages.
Supports multiple languages including Russian and Uzbek.
"""

import logging
import os
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
)

from database import (
    add_reminder,
    get_user_reminders,
    update_reminder_status,
    reschedule_reminder,
    reschedule_reminder_for_followup,
    get_latest_pending_reminder,
    delete_reminder,
    get_user_preferences,
    set_user_preferences,
    check_rate_limit,
)
from config import TRANSCRIPTION_SERVICE, WHISPER_MODEL_SIZE, ELEVENLABS_API_KEY

# Try to import Aisha API key
try:
    from config import AISHA_API_KEY, USE_AISHA
except ImportError:
    AISHA_API_KEY = None
    USE_AISHA = False

# Import transcription based on configured service
if TRANSCRIPTION_SERVICE == "aisha":
    from aisha_transcription import transcribe_audio
    import tempfile
    USE_WHISPER = False
    USE_ELEVENLABS = False
    USE_AISHA_STT = True
elif TRANSCRIPTION_SERVICE == "elevenlabs":
    from elevenlabs_transcription import transcribe_audio
    import tempfile
    USE_WHISPER = False
    USE_ELEVENLABS = True
    USE_AISHA_STT = False
elif TRANSCRIPTION_SERVICE == "whisper":
    from whisper_transcription import transcribe_audio
    import tempfile
    USE_WHISPER = True
    USE_ELEVENLABS = False
    USE_AISHA_STT = False
else:
    from transcription import (
        download_and_transcribe,
        PoorAudioQualityError,
        AudioTooShortError,
        TranscriptionError,
    )
    USE_WHISPER = False
    USE_ELEVENLABS = False
    USE_AISHA_STT = False
from time_parser import (
    parse_reminder_text,
    parse_snooze_duration,
    format_datetime,
    parse_multiple_tasks,
    detect_timezone_from_location,
)
from gemini_parser import parse_with_gemini
from gemini_correction import correct_transcription
from config import RATE_LIMIT_MESSAGES, RATE_LIMIT_WINDOW_SECONDS, USE_GEMINI_FALLBACK, ALWAYS_USE_GEMINI, USE_GEMINI_CORRECTION

logger = logging.getLogger(__name__)

# Conversation states
WAITING_FOR_TIME = 1
WAITING_FOR_CONFIRMATION = 2
WAITING_FOR_SNOOZE = 3
WAITING_FOR_TIMEZONE = 4
WAITING_FOR_TASK_CONFIRMATION = 5


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /start command."""
    user_id = update.effective_user.id
    
    # Initialize user preferences with Tashkent timezone
    prefs = await get_user_preferences(user_id)
    if not prefs:
        await set_user_preferences(user_id, timezone='Asia/Tashkent', language='uz')
    
    welcome_message = """
🎙️ **Eslatma Botiga Xush Kelibsiz!**
**Добро пожаловать в Бот Напоминаний!**

Men ovozli xabarlar orqali eslatmalar yaratishga yordam beraman.
Я помогаю создавать напоминания через голосовые сообщения.

**📝 Eslatma yaratish / Создание напоминаний:**
Ovozli xabar yuboring, masalan:
• _"Ertaga soat 3 da onaga qo'ng'iroq qilish"_
• _"2 soatdan keyin dori ichish"_
• _"Напомни позвонить маме завтра в 3 часа"_
• _"Через 2 часа принять лекарство"_

**⚡ Buyruqlar / Команды:**
/start - Shu xabarni ko'rsatish
/list - Eslatmalaringiz ro'yxati
/help - Batafsil yordam

**🔔 Qanday ishlaydi / Как работает:**
1. Ovozli xabar yuboring
2. Men uni matnga aylantiraman va eslatma yarataman
3. Belgilangan vaqtda sizga xabar yuboraman
4. 1 soatdan keyin: "Vazifa bajarildi?" deb so'rayman
5. HA/ДА - tugallangan, YO'Q/НЕТ - keyinroq eslatish

**Ovozli xabar yuboring!** 🎤
"""
    await update.message.reply_text(welcome_message, parse_mode='Markdown')


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /help command."""
    help_message = """
📚 **Yordam / Помощь**

**Eslatma yaratish / Создание напоминаний:**
Ovozli xabar yuboring:

✅ _"30 minutdan keyin do'konga borish"_
✅ _"Ertaga soat 2 da tish shifokoriga qo'ng'iroq"_
✅ _"Напомни позвонить маме завтра в 3 часа"_
✅ _"Купить продукты через 2 часа"_

**Vaqt iboralari / Выражения времени:**
• "X minutdan/soatdan keyin" / "через X минут/часов"
• "ertaga soat [vaqt]" / "завтра в [время]"
• "bugun soat [vaqt]" / "сегодня в [время]"
• "dushanba/seshanba..." / "понедельник/вторник..."
• Aniq vaqt: "15:00", "3 da"

**Bir nechta vazifa / Несколько задач:**
• _"Soat 3 da Javohirga qo'ng'iroq, keyin soat 5 da uchrashuvga borish"_
• _"Позвонить в банк в 2 часа, и ещё купить продукты в 6"_

**Eslatmadan keyin / После напоминания:**
1 soatdan keyin so'rayman: "Vazifa bajarildi?"
• **HA / ДА** → Tugallandi ✅
• **YO'Q / НЕТ** → Qachon eslatay?

**Kechiktirish / Отложить:**
• _"30 minut"_ / _"30 минут"_
• _"1 soat"_ / _"1 час"_
• _"Ertaga"_ / _"Завтра"_

**Buyruqlar / Команды:**
/start - Boshlash
/list - Eslatmalar ro'yxati
/done [id] - Bajarildi deb belgilash
/delete [id] - O'chirish
/help - Shu yordam

**Muammo bo'lsa / Если проблема:**
🔊 Aniqroq gapiring / Говорите чётче
⏰ Vaqtni aniqroq ayting / Уточните время
"""
    await update.message.reply_text(help_message, parse_mode='Markdown')


async def list_reminders_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /list command to show user's reminders."""
    user_id = update.effective_user.id
    
    # Get user timezone (default Tashkent)
    prefs = await get_user_preferences(user_id)
    user_tz = prefs.get('timezone', 'Asia/Tashkent') if prefs else 'Asia/Tashkent'
    
    reminders = await get_user_reminders(user_id, status='pending')
    
    if not reminders:
        await update.message.reply_text(
            "📭 Sizda eslatmalar yo'q.\n"
            "У вас нет напоминаний.\n\n"
            "Ovozli xabar yuboring! / Отправьте голосовое сообщение!"
        )
        return
    
    message = "📋 **Eslatmalaringiz / Ваши напоминания:**\n\n"
    
    for reminder in reminders:
        scheduled = datetime.fromisoformat(reminder['scheduled_time_utc'])
        formatted_time = format_datetime(scheduled, user_tz)
        
        message += f"**#{reminder['id']}** - {reminder['task_text']}\n"
        
        # Show location if available
        if reminder.get('location'):
            message += f"   📍 {reminder['location']}\n"
        
        # Show notes if available
        if reminder.get('notes'):
            message += f"   📋 {reminder['notes']}\n"
        
        message += f"   ⏰ {formatted_time}\n\n"
    
    message += "_/done [id] - bajarildi | /delete [id] - o'chirish_"
    
    await update.message.reply_text(message, parse_mode='Markdown')


async def done_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /done command to mark a reminder as complete."""
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text(
            "Eslatma ID raqamini kiriting.\n"
            "Укажите ID напоминания.\n\n"
            "Masalan: /done 1\n"
            "/list - ro'yxatni ko'rish"
        )
        return
    
    try:
        reminder_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(
            "Noto'g'ri ID. Raqam kiriting.\n"
            "Неверный ID. Введите число."
        )
        return
    
    await update_reminder_status(reminder_id, 'done')
    await update.message.reply_text(
        f"✅ Eslatma #{reminder_id} bajarildi!\n"
        f"Напоминание #{reminder_id} выполнено!"
    )


async def delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /delete command to remove a reminder."""
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text(
            "Eslatma ID raqamini kiriting.\n"
            "Укажите ID напоминания.\n\n"
            "Masalan: /delete 1\n"
            "/list - ro'yxatni ko'rish"
        )
        return
    
    try:
        reminder_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(
            "Noto'g'ri ID. Raqam kiriting.\n"
            "Неверный ID. Введите число."
        )
        return
    
    deleted = await delete_reminder(reminder_id)
    
    if deleted:
        await update.message.reply_text(
            f"🗑️ Eslatma #{reminder_id} o'chirildi.\n"
            f"Напоминание #{reminder_id} удалено."
        )
    else:
        await update.message.reply_text(
            f"Eslatma #{reminder_id} topilmadi.\n"
            f"Напоминание #{reminder_id} не найдено."
        )


async def timezone_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the /timezone command to set user's timezone."""
    user_id = update.effective_user.id
    
    if context.args:
        # User provided timezone directly
        tz_input = " ".join(context.args)
        detected_tz = detect_timezone_from_location(tz_input)
        
        if detected_tz:
            await set_user_preferences(user_id, timezone=detected_tz)
            await update.message.reply_text(
                f"✅ Vaqt zonasi o'rnatildi: **{detected_tz}**\n"
                f"Часовой пояс установлен: **{detected_tz}**",
                parse_mode='Markdown'
            )
            return ConversationHandler.END
        else:
            # Try to use the input directly as timezone
            try:
                from dateutil import tz as tz_module
                if tz_module.gettz(tz_input):
                    await set_user_preferences(user_id, timezone=tz_input)
                    await update.message.reply_text(
                        f"✅ Vaqt zonasi: **{tz_input}**",
                        parse_mode='Markdown'
                    )
                    return ConversationHandler.END
            except Exception:
                pass
    
    # Show timezone options for Uzbekistan
    keyboard = [
        ['🇺🇿 Toshkent', '🇺🇿 Samarqand'],
        ['🇷🇺 Moskva', '🇰🇿 Olmaota'],
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    
    await update.message.reply_text(
        "🌍 **Vaqt zonasini tanlang / Выберите часовой пояс:**\n\n"
        "Quyidagilardan birini tanlang yoki shahar nomini yozing:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    return WAITING_FOR_TIMEZONE


async def timezone_input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle timezone selection."""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    # Map button text to timezones (Uzbekistan focused)
    tz_map = {
        '🇺🇿 Toshkent': 'Asia/Tashkent',
        '🇺🇿 Samarqand': 'Asia/Samarkand',
        '🇷🇺 Moskva': 'Europe/Moscow',
        '🇰🇿 Olmaota': 'Asia/Almaty',
    }
    
    timezone = tz_map.get(text)
    if not timezone:
        timezone = detect_timezone_from_location(text)
    if not timezone:
        # Try as direct timezone string
        from dateutil import tz as tz_module
        if tz_module.gettz(text):
            timezone = text
    
    if timezone:
        await set_user_preferences(user_id, timezone=timezone)
        await update.message.reply_text(
            f"✅ Vaqt zonasi o'rnatildi: **{timezone}**\n"
            f"Часовой пояс: **{timezone}**",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            "❌ Tushunmadim. Shahar nomini qaytadan yozing.\n"
            "Не понял. Напишите название города ещё раз.",
            reply_markup=ReplyKeyboardRemove()
        )
    
    return ConversationHandler.END


async def voice_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle incoming voice messages - main transcription flow."""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    voice = update.message.voice
    
    # Check rate limiting
    if not await check_rate_limit(user_id, RATE_LIMIT_MESSAGES, RATE_LIMIT_WINDOW_SECONDS):
        await update.message.reply_text(
            "⚠️ Juda ko'p so'rov. Biroz kuting.\n"
            "Слишком много запросов. Подождите."
        )
        return ConversationHandler.END
    
    # Get user preferences (default Tashkent timezone)
    prefs = await get_user_preferences(user_id)
    user_tz = prefs.get('timezone', 'Asia/Tashkent') if prefs else 'Asia/Tashkent'
    user_lang = prefs.get('language', 'uz') if prefs else 'uz'
    
    # Send typing indicator
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    
    try:
        # Step 1: Transcribe the voice message
        await update.message.reply_text(
            "🎧 Ovozli xabaringizni qayta ishlamoqdaman...\n"
            "Обрабатываю голосовое сообщение..."
        )
        
        if USE_WHISPER or USE_ELEVENLABS or USE_AISHA_STT:
            # Download voice file for Whisper, ElevenLabs, or Aisha
            voice_file = await context.bot.get_file(voice.file_id)
            with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp_file:
                voice_path = tmp_file.name
                await voice_file.download_to_drive(voice_path)
            
            logger.info(f"Downloaded voice message to {voice_path} ({os.path.getsize(voice_path)} bytes)")
            
            # Transcribe with selected service
            if USE_AISHA_STT:
                # Use Aisha.group STT (native Uzbek)
                transcription = await transcribe_audio(voice_path, language=user_lang, api_key=AISHA_API_KEY)
            elif USE_ELEVENLABS:
                # Use ElevenLabs Scribe
                transcription = await transcribe_audio(voice_path, language=user_lang, api_key=ELEVENLABS_API_KEY)
            else:
                # Use Whisper
                transcription = await transcribe_audio(voice_path, model_size=WHISPER_MODEL_SIZE)
                
                # Post-correct with Gemini if enabled
                if USE_GEMINI_CORRECTION and transcription:
                    logger.info(f"Original Whisper: {transcription}")
                    transcription = await correct_transcription(transcription, language=user_lang)
                    logger.info(f"After Gemini correction: {transcription}")
            
            detected_lang = user_lang  # Use user preference, auto-detection handled by service
            
            # Clean up temp file
            if os.path.exists(voice_path):
                os.remove(voice_path)
        else:
            # Use Google Cloud STT
            transcription, detected_lang = await download_and_transcribe(
                context.bot,
                voice,
                language_hint=user_lang
            )
        
        # Update user's language preference based on detection
        if detected_lang and detected_lang != user_lang:
            await set_user_preferences(user_id, language=detected_lang)
            user_lang = detected_lang
        
        if not transcription:
            await update.message.reply_text(
                "❌ Ovozli xabarni tushunolmadim.\n"
                "Не удалось распознать голосовое сообщение.\n\n"
                "Aniqroq gapiring va qayta yuboring.\n"
                "Говорите чётче и попробуйте снова."
            )
            return ConversationHandler.END
        
        # Step 2: Check for multiple tasks
        tasks = parse_multiple_tasks(transcription, language=detected_lang)
        
        if len(tasks) > 1:
            # Handle multiple tasks
            return await handle_multiple_tasks(update, context, tasks, user_tz, detected_lang)
        
        # Step 3: Parse the reminder text and time
        # Initialize notes and location
        notes = None
        location = None
        
        # Choose parsing strategy based on configuration
        if ALWAYS_USE_GEMINI:
            # Always use Gemini AI for better understanding
            logger.info("Using Gemini AI for parsing (ALWAYS_USE_GEMINI=true)")
            await update.message.reply_text(
                "🤖 AI yordamida tahlil qilyapman...\n"
                "Анализирую с помощью AI..."
            )
            
            gemini_results = await parse_with_gemini(
                transcription,
                user_timezone=user_tz,
                language=detected_lang
            )
            
            if gemini_results:
                result = gemini_results[0]
                task_text = result["task"]
                scheduled_time = result["time"]
                notes = result.get("notes")
                location = result.get("location")
                logger.info(f"Gemini parsed: {task_text} at {scheduled_time}, notes={notes}, location={location}")
            else:
                # Fallback to regex if Gemini fails
                task_text, scheduled_time = parse_reminder_text(
                    transcription,
                    user_timezone=user_tz,
                    language=detected_lang
                )
        else:
            # Default: try regex first, Gemini as fallback
            task_text, scheduled_time = parse_reminder_text(
                transcription,
                user_timezone=user_tz,
                language=detected_lang
            )
            
            # If regex parsing failed and Gemini is enabled, try Gemini
            if scheduled_time is None and USE_GEMINI_FALLBACK:
                logger.info("Regex parsing failed, trying Gemini AI as fallback...")
                await update.message.reply_text(
                    "🤖 AI yordamida tahlil qilyapman...\n"
                    "Анализирую с помощью AI..."
                )
                
                gemini_results = await parse_with_gemini(
                    transcription,
                    user_timezone=user_tz,
                    language=detected_lang
                )
                
                if gemini_results:
                    # Use the first result from Gemini
                    result = gemini_results[0]
                    task_text = result["task"]
                    scheduled_time = result["time"]
                    notes = result.get("notes")
                    location = result.get("location")
                    logger.info(f"Gemini successfully parsed: {task_text} at {scheduled_time}, notes={notes}, location={location}")
        
        # Store transcription in context for potential re-use
        context.user_data['last_transcription'] = transcription
        context.user_data['task_text'] = task_text
        context.user_data['notes'] = notes
        context.user_data['location'] = location
        context.user_data['user_timezone'] = user_tz
        context.user_data['detected_language'] = detected_lang
        
        if scheduled_time is None:
            # Couldn't parse time - ask user for it
            await update.message.reply_text(
                f"📝 Tushundim: **\"{task_text}\"**\n\n"
                f"⏰ Qachon eslatay? / Когда напомнить?\n\n"
                f"Masalan / Примеры:\n"
                f"• _30 minutdan keyin / через 30 минут_\n"
                f"• _ertaga soat 3 da / завтра в 3 часа_\n"
                f"• _dushanba soat 10 da / в понедельник в 10_",
                parse_mode='Markdown'
            )
            return WAITING_FOR_TIME
        
        # Step 4: Create the reminder
        reminder_id = await add_reminder(
            user_id=user_id,
            chat_id=chat_id,
            task_text=task_text,
            scheduled_time=scheduled_time,
            user_timezone=user_tz,
            notes=notes,
            location=location
        )
        
        formatted_time = format_datetime(scheduled_time, user_tz)
        
        # Build confirmation message with notes and location
        confirmation_msg = (
            f"✅ **Eslatma yaratildi!**\n"
            f"**Напоминание создано!**\n\n"
            f"📝 {task_text}\n"
        )
        
        if location:
            confirmation_msg += f"📍 {location}\n"
        
        if notes:
            confirmation_msg += f"📋 {notes}\n"
        
        confirmation_msg += (
            f"\n⏰ {formatted_time}\n\n"
            f"_Belgilangan vaqtda eslataman._\n"
            f"_Напомню в указанное время._"
        )
        
        await update.message.reply_text(confirmation_msg, parse_mode='Markdown')
        
        logger.info(f"Created reminder {reminder_id} for user {user_id}: {task_text}, notes={notes}, location={location}")
        return ConversationHandler.END
    
    except AudioTooShortError as e:
        await update.message.reply_text(
            f"⚠️ {str(e)}\n\n"
            "Uzunroq xabar yuboring.\n"
            "Отправьте более длинное сообщение."
        )
        return ConversationHandler.END
    
    except PoorAudioQualityError:
        await update.message.reply_text(
            "🔊 **Ovoz sifati muammosi**\n"
            "**Проблема с качеством звука**\n\n"
            "Iltimos:\n"
            "• Aniqroq va sekinroq gapiring\n"
            "• Tinchroq joyda yozing\n"
            "• Telefonni yaqinroq tuting\n\n"
            "Пожалуйста:\n"
            "• Говорите чётче и медленнее\n"
            "• Запишите в тихом месте",
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    
    except TranscriptionError as e:
        logger.error(f"Transcription error: {e}")
        await update.message.reply_text(
            "❌ Xatolik yuz berdi. Keyinroq urinib ko'ring.\n"
            "Произошла ошибка. Попробуйте позже."
        )
        return ConversationHandler.END
    
    except Exception as e:
        logger.error(f"Error processing voice message: {e}")
        await update.message.reply_text(
            "❌ Xatolik yuz berdi. Qayta urinib ko'ring.\n"
            "Что-то пошло не так. Попробуйте ещё раз."
        )
        return ConversationHandler.END


async def handle_multiple_tasks(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    tasks: list,
    user_tz: str,
    detected_lang: str
) -> int:
    """Handle voice message containing multiple tasks."""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    created_reminders = []
    needs_time = []
    
    for task_text in tasks:
        task, scheduled_time = parse_reminder_text(
            task_text,
            user_timezone=user_tz,
            language=detected_lang
        )
        
        if scheduled_time:
            reminder_id = await add_reminder(
                user_id=user_id,
                chat_id=chat_id,
                task_text=task,
                scheduled_time=scheduled_time,
                user_timezone=user_tz
            )
            created_reminders.append((reminder_id, task, scheduled_time))
        else:
            needs_time.append(task)
    
    # Report created reminders
    if created_reminders:
        message = f"✅ **{len(created_reminders)} ta eslatma yaratildi:**\n"
        message += f"**Создано {len(created_reminders)} напоминаний:**\n\n"
        for rid, task, stime in created_reminders:
            formatted_time = format_datetime(stime, user_tz)
            message += f"• {task}\n  ⏰ {formatted_time}\n\n"
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    # Handle tasks that need time
    if needs_time:
        if len(needs_time) == 1:
            context.user_data['task_text'] = needs_time[0]
            context.user_data['user_timezone'] = user_tz
            await update.message.reply_text(
                f"📝 Vazifa: **\"{needs_time[0]}\"**\n\n"
                f"⏰ Qachon eslatay? / Когда напомнить?",
                parse_mode='Markdown'
            )
            return WAITING_FOR_TIME
        else:
            # Multiple tasks need time - save them for sequential processing
            context.user_data['pending_tasks'] = needs_time
            context.user_data['current_task_index'] = 0
            context.user_data['user_timezone'] = user_tz
            
            await update.message.reply_text(
                f"📝 {len(needs_time)} ta vazifa uchun vaqt kerak.\n\n"
                f"Birinchi vazifa: **\"{needs_time[0]}\"**\n"
                f"⏰ Qachon eslatay?",
                parse_mode='Markdown'
            )
            return WAITING_FOR_TIME
    
    return ConversationHandler.END


async def time_input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle time input when we couldn't parse it from the voice message."""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    text = update.message.text
    
    task_text = context.user_data.get('task_text', 'Eslatma')
    user_tz = context.user_data.get('user_timezone', 'Asia/Tashkent')
    detected_lang = context.user_data.get('detected_language')
    
    # Try to parse the time from user's text input
    _, scheduled_time = parse_reminder_text(text, user_timezone=user_tz, language=detected_lang)
    
    if scheduled_time is None:
        # Try parsing as just a time/duration
        duration = parse_snooze_duration(text)
        if duration:
            scheduled_time = datetime.utcnow() + duration
    
    if scheduled_time is None:
        await update.message.reply_text(
            "❌ Vaqtni tushunolmadim. Qayta urinib ko'ring.\n"
            "Не понял время. Попробуйте ещё раз.\n\n"
            "Masalan / Примеры:\n"
            "• _30 minut / 30 минут_\n"
            "• _ertaga soat 3 da / завтра в 3_\n"
            "• _dushanba / понедельник_\n\n"
            "/cancel - bekor qilish",
            parse_mode='Markdown'
        )
        return WAITING_FOR_TIME
    
    # Create the reminder
    reminder_id = await add_reminder(
        user_id=user_id,
        chat_id=chat_id,
        task_text=task_text,
        scheduled_time=scheduled_time,
        user_timezone=user_tz
    )
    
    formatted_time = format_datetime(scheduled_time, user_tz)
    
    await update.message.reply_text(
        f"✅ **Eslatma yaratildi!**\n"
        f"**Напоминание создано!**\n\n"
        f"📝 {task_text}\n"
        f"⏰ {formatted_time}",
        parse_mode='Markdown'
    )
    
    # Check if there are more pending tasks
    pending_tasks = context.user_data.get('pending_tasks', [])
    current_idx = context.user_data.get('current_task_index', 0)
    
    if pending_tasks and current_idx + 1 < len(pending_tasks):
        # Move to next task
        next_idx = current_idx + 1
        context.user_data['current_task_index'] = next_idx
        context.user_data['task_text'] = pending_tasks[next_idx]
        
        await update.message.reply_text(
            f"📝 Keyingi vazifa: **\"{pending_tasks[next_idx]}\"**\n"
            f"⏰ Qachon eslatay?",
            parse_mode='Markdown'
        )
        return WAITING_FOR_TIME
    
    # Clear user data
    context.user_data.clear()
    
    return ConversationHandler.END


async def yes_no_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle YES/NO button clicks for follow-up questions."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    action = query.data  # "reminder_yes" or "reminder_no"
    
    # Get the most recent reminder that had a follow-up sent
    reminder = await get_latest_pending_reminder(user_id)
    
    if not reminder:
        await query.edit_message_text(
            "❌ Eslatma topilmadi.\n"
            "Напоминание не найдено."
        )
        return
    
    if action == "reminder_yes":
        # Mark as done
        await update_reminder_status(reminder['id'], 'done')
        await query.edit_message_text(
            f"✅ **Ajoyib!** Vazifa bajarildi!\n"
            f"**Отлично!** Задача выполнена!\n\n"
            f"📝 _{reminder['task_text']}_",
            parse_mode='Markdown'
        )
    
    elif action == "reminder_no":
        # Automatically reschedule for 30 minutes later
        new_time = datetime.utcnow() + timedelta(minutes=30)
        await reschedule_reminder_for_followup(reminder['id'], new_time)
        
        await query.edit_message_text(
            f"⏰ **Tushunarli!** 30 minut ichida yana eslataman.\n"
            f"**Понятно!** Напомню снова через 30 минут.\n\n"
            f"📝 _{reminder['task_text']}_",
            parse_mode='Markdown'
        )


async def yes_no_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle YES/NO text responses (legacy support). Supports Uzbek and Russian."""
    user_id = update.effective_user.id
    text = update.message.text.strip().upper()
    
    # Get the most recent reminder that had a follow-up sent
    reminder = await get_latest_pending_reminder(user_id)
    
    if not reminder:
        # No pending reminder with follow-up - might be out of context
        return ConversationHandler.END
    
    # Positive responses (Uzbek and Russian)
    positive = ['HA', 'XA', 'ХА', 'BAJARILDI', 'TAYYOR', 'TUGADI', 'ДА', 'Д', 'ГОТОВО', 'ВЫПОЛНЕНО', '✅']
    # Negative responses (Uzbek and Russian)
    negative = ["YO'Q", 'YOQ', 'YOʻQ', 'ЙУҚ', 'HALI', 'KEYINROQ', 'НЕТ', 'Н', 'ЕЩЁ НЕТ', 'ПОЗЖЕ', 'ОТЛОЖИТЬ']
    
    if text in positive:
        # Mark as done
        await update_reminder_status(reminder['id'], 'done')
        await update.message.reply_text(
            f"✅ **Ajoyib!** Vazifa bajarildi!\n"
            f"**Отлично!** Задача выполнена!\n\n"
            f"📝 _{reminder['task_text']}_",
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    
    elif text in negative:
        # Automatically reschedule for 30 minutes later
        new_time = datetime.utcnow() + timedelta(minutes=30)
        await reschedule_reminder_for_followup(reminder['id'], new_time)
        
        await update.message.reply_text(
            f"⏰ **Tushunarli!** 30 minut ichida yana eslataman.\n"
            f"**Понятno!** Напомню снова через 30 минут.\n\n"
            f"📝 _{reminder['task_text']}_",
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    
    return ConversationHandler.END


async def snooze_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle snooze duration input."""
    text = update.message.text.strip().lower()
    
    reminder_id = context.user_data.get('snooze_reminder_id')
    task_text = context.user_data.get('snooze_task_text', 'Eslatma')
    user_tz = context.user_data.get('user_timezone', 'Asia/Tashkent')
    
    if not reminder_id:
        await update.message.reply_text(
            "Qaysi eslatmani kechiktirishni bilmayapman.\n"
            "Не знаю, какое напоминание отложить.\n\n"
            "/list - eslatmalar ro'yxati"
        )
        return ConversationHandler.END
    
    # Parse the snooze duration (Uzbek and Russian)
    if text in ['ertaga', 'завтра', 'ertaga / завтра']:
        new_time = datetime.utcnow().replace(hour=4, minute=0, second=0, microsecond=0)  # 9:00 Tashkent = 04:00 UTC
        new_time += timedelta(days=1)
    else:
        # Handle the keyboard button values (Uzbek)
        uzbek_duration_map = {
            '15 minut': timedelta(minutes=15),
            '30 minut': timedelta(minutes=30),
            '1 soat': timedelta(hours=1),
            '2 soat': timedelta(hours=2),
        }
        
        if text in uzbek_duration_map:
            duration = uzbek_duration_map[text]
        else:
            duration = parse_snooze_duration(text)
        
        if duration:
            new_time = datetime.utcnow() + duration
        else:
            await update.message.reply_text(
                "❌ Tushunmadim. Masalan:\n"
                "• _30 minut / 30 минут_\n"
                "• _1 soat / 1 час_\n"
                "• _2 soat / 2 часа_",
                reply_markup=ReplyKeyboardRemove(),
                parse_mode='Markdown'
            )
            return WAITING_FOR_SNOOZE
    
    # Reschedule the reminder
    await reschedule_reminder(reminder_id, new_time)
    
    formatted_time = format_datetime(new_time, user_tz)
    
    await update.message.reply_text(
        f"✅ **Eslatma ko'chirildi!**\n"
        f"**Напоминание перенесено!**\n\n"
        f"📝 {task_text}\n"
        f"⏰ {formatted_time}",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode='Markdown'
    )
    
    # Clear user data
    context.user_data.clear()
    
    return ConversationHandler.END


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the /cancel command to exit conversation."""
    context.user_data.clear()
    await update.message.reply_text(
        "❌ Bekor qilindi. Yangi eslatma uchun ovozli xabar yuboring.\n"
        "Отменено. Отправьте голосовое сообщение.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


async def unknown_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle any unknown text messages."""
    # Check if this might be a YES/NO response (Uzbek or Russian)
    text = update.message.text.strip().upper()
    
    positive = ['HA', 'XA', 'ХА', 'BAJARILDI', 'TAYYOR', 'TUGADI',
                'ДА', 'Д', 'ГОТОВО', 'ВЫПОЛНЕНО', '✅']
    negative = ["YO'Q", 'YOQ', 'YOʻQ', 'ЙУҚ', 'HALI', 'KEYINROQ',
                'НЕТ', 'Н', 'ЕЩЁ НЕТ', 'ПОЗЖЕ', 'ОТЛОЖИТЬ']
    
    if text in positive + negative:
        # Try to handle as YES/NO
        await yes_no_handler(update, context)
        return
    
    await update.message.reply_text(
        "🎤 Eslatma yaratish uchun **ovozli xabar** yuboring.\n"
        "Отправьте **голосовое сообщение** для напоминания.\n\n"
        "Buyruqlar / Команды:\n"
        "/list - Eslatmalar / Напоминания\n"
        "/help - Yordam / Помощь",
        parse_mode='Markdown'
    )


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors in the bot."""
    logger.error(f"Exception while handling an update: {context.error}")
    
    # Don't send error messages for certain types of errors
    if update and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "❌ Xatolik yuz berdi. Qayta urinib ko'ring.\n"
                "Произошла ошибка. Попробуйте ещё раз."
            )
        except Exception:
            pass  # Can't send message, ignore
