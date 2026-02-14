"""
FastAPI Backend Server for Levi Mobile App
Full-featured API with voice transcription, AI parsing, recurring reminders,
push notifications, and Turso cloud database support.
"""

import os
import jwt
import hashlib
import asyncio
import logging
import tempfile
import json
import random
import httpx
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, Header, UploadFile, File, BackgroundTasks, Body, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
JWT_SECRET = os.environ.get('JWT_SECRET', 'levi-app-secret-key-change-in-production')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24 * 30  # 30 days
FOLLOW_UP_DELAY_SECONDS = 1800  # 30 minutes
DEFAULT_TIMEZONE = 'Asia/Tashkent'
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'levi2026admin')

# OTP Storage (in-memory fallback, expires after 5 minutes)
# Format: {phone: {"code": "123456", "expires": datetime, "attempts": 0}}
otp_storage: Dict[str, dict] = {}

# Unimtx OTP Service Configuration
UNIMTX_ACCESS_KEY_ID = os.environ.get('UNIMTX_ACCESS_KEY_ID', '')
UNIMTX_API_BASE = 'https://api.unimtx.com'
UNIMTX_ENABLED = bool(UNIMTX_ACCESS_KEY_ID)

# API Keys
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
ELEVENLABS_API_KEY = os.environ.get('ELEVENLABS_API_KEY')

# Turso Database Configuration
TURSO_DATABASE_URL = os.environ.get('TURSO_DATABASE_URL')
TURSO_AUTH_TOKEN = os.environ.get('TURSO_AUTH_TOKEN')
USE_TURSO = bool(TURSO_DATABASE_URL and TURSO_AUTH_TOKEN)
DATABASE_PATH = os.environ.get('DATABASE_PATH', 'reminders.db')

# Firebase Cloud Messaging (for push notifications)
FCM_SERVER_KEY = os.environ.get('FCM_SERVER_KEY')

# Try to import libsql for Turso
LIBSQL_AVAILABLE = False
libsql = None
try:
    import libsql_experimental as libsql
    LIBSQL_AVAILABLE = True
    logger.info("libsql_experimental available")
except ImportError:
    try:
        import libsql_client as libsql
        LIBSQL_AVAILABLE = True
    except ImportError:
        logger.warning("No libsql library available")

# Import Gemini
try:
    import google.generativeai as genai
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_model = genai.GenerativeModel('models/gemini-2.0-flash')
    else:
        gemini_model = None
except ImportError:
    gemini_model = None
    logger.warning("google.generativeai not available")

# Import ElevenLabs
try:
    from elevenlabs.client import ElevenLabs
    ELEVENLABS_AVAILABLE = True
except ImportError:
    ELEVENLABS_AVAILABLE = False
    logger.warning("elevenlabs not available")

# Fallback to aiosqlite if Turso not available
import aiosqlite


def get_db_connection():
    """Get database connection (Turso or local SQLite)."""
    if USE_TURSO and LIBSQL_AVAILABLE and libsql:
        try:
            conn = libsql.connect(TURSO_DATABASE_URL, auth_token=TURSO_AUTH_TOKEN)
            logger.info("Connected to Turso")
            return conn
        except Exception as e:
            logger.error(f"Turso connection failed: {e}")
    return None  # Will use aiosqlite


def rows_to_dicts(cursor, rows) -> List[dict]:
    """Convert rows to list of dictionaries."""
    if not rows:
        return []
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in rows]


def row_to_dict(cursor, row) -> Optional[dict]:
    """Convert single row to dictionary."""
    if not row:
        return None
    columns = [desc[0] for desc in cursor.description]
    return dict(zip(columns, row))


# Background scheduler task
scheduler_running = False


async def reminder_scheduler():
    """Background task to check and send reminder notifications."""
    global scheduler_running
    scheduler_running = True
    logger.info("Reminder scheduler started")
    
    while scheduler_running:
        try:
            await check_and_send_reminders()
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
        await asyncio.sleep(30)  # Check every 30 seconds


async def check_and_send_reminders():
    """Check for due reminders and send push notifications."""
    now = datetime.utcnow()
    
    if USE_TURSO and LIBSQL_AVAILABLE:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT r.id, r.user_id, r.task_text, r.notes, r.location, 
                       r.scheduled_time_utc, r.recurrence_type, r.recurrence_time,
                       r.user_timezone, u.fcm_token, u.name
                FROM app_reminders r
                JOIN app_users u ON r.user_id = u.id
                WHERE r.status = 'pending' 
                AND r.initial_reminder_sent = 0
                AND r.scheduled_time_utc <= ?
                """,
                (now.isoformat(),)
            )
            rows = cursor.fetchall()
            reminders = rows_to_dicts(cursor, rows)
            conn.close()
            
            for reminder in reminders:
                await send_push_notification(reminder)
                await mark_reminder_sent(reminder['id'])
                
                # Schedule next occurrence for recurring reminders
                if reminder.get('recurrence_type'):
                    await schedule_next_recurrence(reminder)
    else:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT r.id, r.user_id, r.task_text, r.notes, r.location, 
                       r.scheduled_time_utc, r.recurrence_type, r.recurrence_time,
                       r.user_timezone, u.fcm_token, u.name
                FROM app_reminders r
                JOIN app_users u ON r.user_id = u.id
                WHERE r.status = 'pending' 
                AND r.initial_reminder_sent = 0
                AND r.scheduled_time_utc <= ?
                """,
                (now.isoformat(),)
            )
            rows = await cursor.fetchall()
            
            for row in rows:
                reminder = dict(row)
                await send_push_notification(reminder)
                await mark_reminder_sent_async(db, reminder['id'])
                
                if reminder.get('recurrence_type'):
                    await schedule_next_recurrence_async(db, reminder)
            
            await db.commit()


async def send_push_notification(reminder: dict):
    """Send push notification via Firebase Cloud Messaging."""
    fcm_token = reminder.get('fcm_token')
    if not fcm_token or not FCM_SERVER_KEY:
        logger.info(f"No FCM token/key for reminder {reminder['id']}, skipping push")
        return
    
    try:
        import httpx
        
        message = f"🔔 {reminder['task_text']}"
        if reminder.get('notes'):
            message += f"\n📋 {reminder['notes']}"
        if reminder.get('location'):
            message += f"\n📍 {reminder['location']}"
        
        payload = {
            "to": fcm_token,
            "notification": {
                "title": "Levi - Eslatma",
                "body": message,
                "sound": "default"
            },
            "data": {
                "reminder_id": str(reminder['id']),
                "task_text": reminder['task_text']
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://fcm.googleapis.com/fcm/send",
                json=payload,
                headers={
                    "Authorization": f"key={FCM_SERVER_KEY}",
                    "Content-Type": "application/json"
                }
            )
            logger.info(f"FCM response: {response.status_code}")
    except Exception as e:
        logger.error(f"FCM push failed: {e}")


async def mark_reminder_sent(reminder_id: int):
    """Mark reminder as sent (Turso)."""
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE app_reminders SET initial_reminder_sent = 1 WHERE id = ?",
            (reminder_id,)
        )
        conn.commit()
        conn.close()


async def mark_reminder_sent_async(db, reminder_id: int):
    """Mark reminder as sent (aiosqlite)."""
    await db.execute(
        "UPDATE app_reminders SET initial_reminder_sent = 1 WHERE id = ?",
        (reminder_id,)
    )


async def schedule_next_recurrence(reminder: dict):
    """Schedule next occurrence for recurring reminder (Turso)."""
    from dateutil import tz as tz_module
    
    recurrence_type = reminder.get('recurrence_type')
    if not recurrence_type:
        return
    
    recurrence_time = reminder.get('recurrence_time', '09:00')
    user_tz = reminder.get('user_timezone', DEFAULT_TIMEZONE)
    
    try:
        hour, minute = map(int, recurrence_time.split(':'))
    except:
        hour, minute = 9, 0
    
    user_timezone = tz_module.gettz(user_tz)
    now_local = datetime.now(user_timezone)
    
    if recurrence_type == 'daily':
        next_date = now_local + timedelta(days=1)
    elif recurrence_type == 'weekdays':
        next_date = now_local + timedelta(days=1)
        while next_date.weekday() >= 5:
            next_date += timedelta(days=1)
    elif recurrence_type == 'weekly':
        next_date = now_local + timedelta(weeks=1)
    elif recurrence_type == 'monthly':
        next_month = now_local.month + 1
        next_year = now_local.year
        if next_month > 12:
            next_month = 1
            next_year += 1
        try:
            next_date = now_local.replace(year=next_year, month=next_month)
        except ValueError:
            next_date = now_local.replace(year=next_year, month=next_month, day=28)
    else:
        return
    
    next_datetime_local = next_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
    next_datetime_utc = next_datetime_local.astimezone(tz_module.UTC).replace(tzinfo=None)
    
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO app_reminders (user_id, task_text, notes, location, scheduled_time_utc, 
                                       user_timezone, recurrence_type, recurrence_time, initial_reminder_sent)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
            """,
            (reminder['user_id'], reminder['task_text'], reminder.get('notes'), 
             reminder.get('location'), next_datetime_utc.isoformat(),
             user_tz, recurrence_type, recurrence_time)
        )
        conn.commit()
        conn.close()
        logger.info(f"Scheduled next occurrence for reminder {reminder['id']}")


async def schedule_next_recurrence_async(db, reminder: dict):
    """Schedule next occurrence (aiosqlite version)."""
    from dateutil import tz as tz_module
    
    recurrence_type = reminder.get('recurrence_type')
    if not recurrence_type:
        return
    
    recurrence_time = reminder.get('recurrence_time', '09:00')
    user_tz = reminder.get('user_timezone', DEFAULT_TIMEZONE)
    
    try:
        hour, minute = map(int, recurrence_time.split(':'))
    except:
        hour, minute = 9, 0
    
    user_timezone = tz_module.gettz(user_tz)
    now_local = datetime.now(user_timezone)
    
    if recurrence_type == 'daily':
        next_date = now_local + timedelta(days=1)
    elif recurrence_type == 'weekdays':
        next_date = now_local + timedelta(days=1)
        while next_date.weekday() >= 5:
            next_date += timedelta(days=1)
    elif recurrence_type == 'weekly':
        next_date = now_local + timedelta(weeks=1)
    elif recurrence_type == 'monthly':
        next_month = now_local.month + 1
        next_year = now_local.year
        if next_month > 12:
            next_month = 1
            next_year += 1
        try:
            next_date = now_local.replace(year=next_year, month=next_month)
        except ValueError:
            next_date = now_local.replace(year=next_year, month=next_month, day=28)
    else:
        return
    
    next_datetime_local = next_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
    next_datetime_utc = next_datetime_local.astimezone(tz_module.UTC).replace(tzinfo=None)
    
    await db.execute(
        """
        INSERT INTO app_reminders (user_id, task_text, notes, location, scheduled_time_utc, 
                                   user_timezone, recurrence_type, recurrence_time, initial_reminder_sent)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
        """,
        (reminder['user_id'], reminder['task_text'], reminder.get('notes'), 
         reminder.get('location'), next_datetime_utc.isoformat(),
         user_tz, recurrence_type, recurrence_time)
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - start/stop background tasks."""
    # Startup
    await init_app_database()
    scheduler_task = asyncio.create_task(reminder_scheduler())
    logger.info("Application started")
    
    yield
    
    # Shutdown
    global scheduler_running
    scheduler_running = False
    scheduler_task.cancel()
    logger.info("Application shutdown")


app = FastAPI(title="Levi API", version="2.0.0", lifespan=lifespan)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===== Pydantic Models =====
class LoginRequest(BaseModel):
    phone: str
    password: str


class RegisterRequest(BaseModel):
    name: str
    phone: str
    password: str


class UserResponse(BaseModel):
    id: int
    phone: str
    name: str
    timezone: str
    language: str
    created_at: str


class AuthResponse(BaseModel):
    success: bool
    user: Optional[UserResponse] = None
    token: Optional[str] = None
    message: Optional[str] = None


class OtpRequest(BaseModel):
    phone: str


class OtpVerifyRequest(BaseModel):
    phone: str
    otp: str
    name: Optional[str] = None
    password: Optional[str] = None
    isLogin: Optional[bool] = False


class OtpResponse(BaseModel):
    success: bool
    message: Optional[str] = None


class ReminderCreate(BaseModel):
    task_text: str
    scheduled_time: str
    notes: Optional[str] = None
    location: Optional[str] = None
    recurrence_type: Optional[str] = None
    recurrence_time: Optional[str] = None


class ReminderResponse(BaseModel):
    id: int
    user_id: int
    task_text: str
    scheduled_time_utc: str
    user_timezone: str
    status: str
    notes: Optional[str] = None
    location: Optional[str] = None
    recurrence_type: Optional[str] = None
    recurrence_time: Optional[str] = None
    created_at: str


class VoiceParseResponse(BaseModel):
    success: bool
    transcription: Optional[str] = None
    reminders: Optional[List[dict]] = None
    message: Optional[str] = None


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    timezone: Optional[str] = None
    fcm_token: Optional[str] = None


class PasswordUpdate(BaseModel):
    current_password: str
    new_password: str


class FCMTokenUpdate(BaseModel):
    fcm_token: str


# ===== Database Initialization =====
async def init_app_database():
    """Initialize app-specific tables."""
    db_type = "Turso" if USE_TURSO else "SQLite"
    logger.info(f"Initializing {db_type} database...")
    
    if USE_TURSO and LIBSQL_AVAILABLE:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS app_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    phone TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    name TEXT NOT NULL,
                    timezone TEXT DEFAULT 'Asia/Tashkent',
                    language TEXT DEFAULT 'uz',
                    fcm_token TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS app_reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    task_text TEXT NOT NULL,
                    notes TEXT,
                    location TEXT,
                    scheduled_time_utc TIMESTAMP NOT NULL,
                    user_timezone TEXT DEFAULT 'Asia/Tashkent',
                    status TEXT DEFAULT 'pending',
                    recurrence_type TEXT,
                    recurrence_time TEXT,
                    initial_reminder_sent INTEGER DEFAULT 0,
                    follow_up_sent INTEGER DEFAULT 0,
                    audio_url TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES app_users(id)
                )
            """)
            
            conn.commit()
            conn.close()
            logger.info("Turso database initialized")
            return
    
    # Fallback to aiosqlite
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS app_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                name TEXT NOT NULL,
                timezone TEXT DEFAULT 'Asia/Tashkent',
                language TEXT DEFAULT 'uz',
                fcm_token TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS app_reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                task_text TEXT NOT NULL,
                notes TEXT,
                location TEXT,
                scheduled_time_utc TIMESTAMP NOT NULL,
                user_timezone TEXT DEFAULT 'Asia/Tashkent',
                status TEXT DEFAULT 'pending',
                recurrence_type TEXT,
                recurrence_time TEXT,
                initial_reminder_sent INTEGER DEFAULT 0,
                follow_up_sent INTEGER DEFAULT 0,
                audio_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES app_users(id)
            )
        """)
        
        await db.commit()
        logger.info("SQLite database initialized")


# ===== Utility Functions =====
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    return hash_password(password) == password_hash


def create_jwt_token(user_id: int) -> str:
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_jwt_token(token: str) -> Optional[int]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload.get('user_id')
    except:
        return None


async def get_current_user(authorization: Optional[str] = Header(None)) -> int:
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    
    if not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    
    token = authorization[7:]
    user_id = decode_jwt_token(token)
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return user_id


# ===== Voice Transcription =====

async def normalize_transcription(raw_text: str) -> str:
    """
    Use Gemini to normalize transcription output to clean Uzbek Latin or Russian.
    Fixes cases where ElevenLabs outputs Turkish, Kazakh, Kyrgyz, or Uzbek Cyrillic.
    """
    if not gemini_model or not raw_text or len(raw_text.strip()) < 2:
        return raw_text
    
    try:
        prompt = f"""Sen transkripsiya natijasini to'g'irlash uchun yordamchisan.

Quyidagi matn ovozdan yozilgan, lekin noto'g'ri til sifatida aniqlangan bo'lishi mumkin (turk, qozoq, qirg'iz, o'zbek kirill yoki boshqa).

Asl transkripsiya: "{raw_text}"

VAZIFA:
1. Agar matn o'zbek tilida aytilgan bo'lsa — uni O'ZBEK LOTIN ALIFBOSIDA qayta yoz (to'g'ri imlo bilan)
2. Agar matn rus tilida aytilgan bo'lsa — uni RUSCHA qoldir (kirill alifbosida)
3. Turk, qozoq, qirg'iz so'zlarini o'zbek ekvivalentiga almashtir
4. O'zbek kirill harflarini lotin harflariga o'gir (ш→sh, ч→ch, ғ→g', ў→o', қ→q, ҳ→h va h.k.)
5. Hech qanday qo'shimcha izoh yoki tushuntirish YOZMA — faqat toza matnni qaytar

FAQAT toza, to'g'irlangan matnni qaytar, boshqa hech narsa yo'q:"""

        response = gemini_model.generate_content(prompt)
        normalized = response.text.strip()
        
        # Remove any markdown formatting or quotes Gemini might add
        if normalized.startswith('"') and normalized.endswith('"'):
            normalized = normalized[1:-1]
        if normalized.startswith("'") and normalized.endswith("'"):
            normalized = normalized[1:-1]
        if normalized.startswith('```') and normalized.endswith('```'):
            normalized = normalized[3:-3].strip()
        
        if len(normalized) > 0:
            logger.info(f"Transcription normalized: '{raw_text}' → '{normalized}'")
            return normalized
        return raw_text
    except Exception as e:
        logger.warning(f"Transcription normalization failed: {e}")
        return raw_text


async def transcribe_audio_elevenlabs(file_path: str, language: str = "uz") -> Optional[str]:
    """Transcribe audio using ElevenLabs Scribe, then normalize to Uzbek Latin or Russian."""
    if not ELEVENLABS_AVAILABLE or not ELEVENLABS_API_KEY:
        logger.warning("ElevenLabs not available")
        return None
    
    try:
        client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
        
        with open(file_path, 'rb') as audio_file:
            # Always force Uzbek — we normalize to Latin/Russian after
            language_code = "uzb" if language == "uz" else "rus" if language == "ru" else "uzb"
            
            result = client.speech_to_text.convert(
                file=audio_file,
                model_id="scribe_v2",
                language_code=language_code
            )
            
            raw_text = result.text.strip() if hasattr(result, 'text') else str(result).strip()
            
            if not raw_text:
                return None
            
            logger.info(f"ElevenLabs raw transcription (lang={language_code}): '{raw_text}'")
            
            # Normalize: fix Cyrillic/Turkish/Kazakh → clean Uzbek Latin or Russian
            normalized = await normalize_transcription(raw_text)
            return normalized
    except Exception as e:
        logger.error(f"ElevenLabs transcription error: {e}")
        return None


# ===== Gemini AI Parsing =====
async def parse_with_gemini(text: str, user_timezone: str = DEFAULT_TIMEZONE) -> List[dict]:
    """Use Gemini AI to parse reminder text - same logic as Telegram bot."""
    if not gemini_model:
        logger.warning("Gemini not available")
        return []
    
    try:
        now_utc = datetime.utcnow()
        logger.info(f"=== PARSE_WITH_GEMINI START ===")
        logger.info(f"Current UTC time (server): {now_utc.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"User timezone: {user_timezone}")
        logger.info(f"Input text: {text}")
        
        # Use the same comprehensive prompt as gemini_parser.py
        prompt = f"""Siz O'zbekiston foydalanuvchilari uchun aqlli eslatma yordamchisisiz. Quyidagi matnni tahlil qiling va eslatma vazifalarini ajratib oling.

Hozirgi sana va vaqt (UTC): {now_utc.strftime('%Y-%m-%d %H:%M')}
Foydalanuvchi vaqt zonasi: {user_timezone}

Matn: "{text}"

MUHIM QOIDALAR:
1. BARCHA javoblarni O'ZBEK TILIDA yozing!
2. Inglizcha so'zlarni O'ZBEK TILIGA tarjima qiling!
3. Vazifa tavsifi qisqa va harakat yo'naltirilgan bo'lsin

Har bir eslatma uchun aniqlang:
1. Vazifa tavsifi (qisqa, O'ZBEK TILIDA) - masalan: "Kitob o'qish", "Dori ichish", "Uyga qaytish"
2. Rejalashtirilgan vaqt UTC formatida (ISO: YYYY-MM-DD HH:MM)
3. Izohlar/tafsilotlar
4. Joylashuv (agar aytilgan bo'lsa)
5. Takrorlanish turi: "daily", "weekly", "weekdays", "monthly" yoki null
6. Takrorlanish vaqti (HH:MM foydalanuvchi vaqt zonasida)

TARJIMA QOIDALARI:
- "return home" = "Uyga qaytish"
- "read book" / "read" = "Kitob o'qish"
- "take medicine" = "Dori ichish"
- "go to store" / "shopping" = "Do'konga borish"
- "call" = "Qo'ng'iroq qilish"
- "meet" / "meeting" = "Uchrashuv"
- "exercise" / "workout" = "Mashq qilish"
- "study" = "O'qish"
- "work" = "Ishlash"
- "cook" = "Ovqat tayyorlash"
- "clean" = "Tozalash"
- "sleep" = "Uxlash"
- "wake up" = "Uyg'onish"

VAQTNI TAHLIL QILISH QOIDALARI:
O'zbek raqamlari:
- "bir" = 1, "ikki" = 2, "uch" = 3, "to'rt" = 4, "besh" = 5
- "olti" = 6, "yetti" = 7, "sakkiz" = 8, "to'qqiz" = 9, "o'n" = 10
- "o'n bir" = 11, "o'n ikki" = 12

Vaqt iboralari:
- "soat o'n da" / "soat 10 da" = 10:00
- "ertalab" = 8:00 AM (agar aniq vaqt berilmagan bo'lsa)
- "kechqurun" / "oqshom" = 18:00 (agar aniq vaqt berilmagan bo'lsa)
- "tushlik" = 13:00
- "ertaga" = ertangi kun soat 9:00
- "bugun" = bugungi kun
- "5 minut" / "5 daqiqa" / "besh minutdan keyin" = 5 daqiqadan keyin
- "yarim soat" = 30 daqiqadan keyin
- "bir soatdan keyin" = 1 soatdan keyin

Takrorlanish:
- "har kuni" = daily
- "har hafta" = weekly
- "har oy" = monthly
- "ish kunlari" = weekdays

Faqat JSON massivini qaytaring:
[
  {{"task": "vazifa O'ZBEK TILIDA", "time_utc": "2026-01-25 14:00", "notes": "izoh yoki null", "location": "joy yoki null", "recurrence_type": null, "recurrence_time": null}}
]

Agar eslatma bo'lmasa: []
"""
        
        response = gemini_model.generate_content(prompt)
        result_text = response.text.strip()
        
        logger.info(f"Gemini raw response: {result_text[:500]}")
        logger.info(f"Time after Gemini call: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Extract JSON
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0].strip()
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0].strip()
        
        reminders = json.loads(result_text)
        
        if not isinstance(reminders, list):
            return []
        
        # Process reminders - handle past times
        processed = []
        for r in reminders:
            if not isinstance(r, dict) or 'task' not in r or 'time_utc' not in r:
                continue
            
            time_str = r.get('time_utc', '')
            logger.info(f"Processing reminder: task='{r.get('task')}', time_utc='{time_str}'")
            try:
                scheduled_time = datetime.strptime(time_str, '%Y-%m-%d %H:%M')
                diff_seconds = (scheduled_time - now_utc).total_seconds()
                logger.info(f"Raw scheduled time diff from now_utc: {diff_seconds:.0f} seconds ({diff_seconds/60:.1f} minutes)")
                
                # FIX: Gemini returns HH:MM without seconds, causing alarms to fire early.
                # If the scheduled time is within 10 minutes of now, add the current seconds
                # to prevent rounding down. This ensures "5 minutdan keyin" at 12:30:42
                # becomes 12:35:42 instead of 12:35:00
                if 0 < diff_seconds < 600:  # Within 10 minutes
                    current_seconds = now_utc.second
                    scheduled_time = scheduled_time.replace(second=current_seconds)
                    # If adding seconds makes it slightly in the past, add 1 minute
                    if scheduled_time <= now_utc:
                        scheduled_time = scheduled_time + timedelta(minutes=1)
                    diff_seconds = (scheduled_time - now_utc).total_seconds()
                    logger.info(f"Adjusted for seconds: new time = {scheduled_time.strftime('%Y-%m-%d %H:%M:%S')}, diff = {diff_seconds:.0f}s")
                    r['time_utc'] = scheduled_time.strftime('%Y-%m-%d %H:%M:%S')
                
                # If time is in the past for non-recurring, skip
                if scheduled_time <= now_utc and not r.get('recurrence_type'):
                    logger.warning(f"Skipping past time: {time_str}")
                    continue
                
                # For recurring reminders with past times, schedule for next occurrence
                if scheduled_time <= now_utc and r.get('recurrence_type'):
                    recurrence = r.get('recurrence_type')
                    if recurrence == 'daily':
                        scheduled_time = scheduled_time + timedelta(days=1)
                    elif recurrence == 'weekly':
                        scheduled_time = scheduled_time + timedelta(weeks=1)
                    r['time_utc'] = scheduled_time.strftime('%Y-%m-%d %H:%M:%S')
                    logger.info(f"Rescheduled recurring reminder to: {r['time_utc']}")
                
                processed.append(r)
                logger.info(f"FINAL scheduled_time_utc: {r['time_utc']}")
            except ValueError as e:
                logger.error(f"Failed to parse time '{time_str}': {e}")
                continue
        
        logger.info(f"=== PARSE_WITH_GEMINI END - {len(processed)} reminders ===")
        return processed
    
    except Exception as e:
        logger.error(f"Gemini parsing error: {e}")
        return []


# ===== Auth Endpoints =====
@app.post("/api/auth/register", response_model=AuthResponse)
async def register(data: RegisterRequest):
    """Register a new user."""
    if USE_TURSO and LIBSQL_AVAILABLE:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM app_users WHERE phone = ?", (data.phone,))
            if cursor.fetchone():
                conn.close()
                return AuthResponse(success=False, message="Telefon raqam allaqachon ro'yxatdan o'tgan")
            
            password_hash = hash_password(data.password)
            cursor.execute(
                "INSERT INTO app_users (phone, password_hash, name) VALUES (?, ?, ?)",
                (data.phone, password_hash, data.name)
            )
            conn.commit()
            user_id = cursor.lastrowid
            
            cursor.execute(
                "SELECT id, phone, name, timezone, language, created_at FROM app_users WHERE id = ?",
                (user_id,)
            )
            row = cursor.fetchone()
            conn.close()
            
            user = UserResponse(id=row[0], phone=row[1], name=row[2], timezone=row[3], language=row[4], created_at=str(row[5]))
            token = create_jwt_token(user_id)
            return AuthResponse(success=True, user=user, token=token)
    
    # Fallback to aiosqlite
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("SELECT id FROM app_users WHERE phone = ?", (data.phone,))
        if await cursor.fetchone():
            return AuthResponse(success=False, message="Telefon raqam allaqachon ro'yxatdan o'tgan")
        
        password_hash = hash_password(data.password)
        cursor = await db.execute(
            "INSERT INTO app_users (phone, password_hash, name) VALUES (?, ?, ?)",
            (data.phone, password_hash, data.name)
        )
        await db.commit()
        user_id = cursor.lastrowid
        
        cursor = await db.execute(
            "SELECT id, phone, name, timezone, language, created_at FROM app_users WHERE id = ?",
            (user_id,)
        )
        row = await cursor.fetchone()
        
        user = UserResponse(id=row[0], phone=row[1], name=row[2], timezone=row[3], language=row[4], created_at=str(row[5]))
        token = create_jwt_token(user_id)
        return AuthResponse(success=True, user=user, token=token)


@app.post("/api/auth/login", response_model=AuthResponse)
async def login(data: LoginRequest):
    """Login user."""
    if USE_TURSO and LIBSQL_AVAILABLE:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, phone, password_hash, name, timezone, language, created_at FROM app_users WHERE phone = ?",
                (data.phone,)
            )
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return AuthResponse(success=False, message="Telefon raqam yoki parol noto'g'ri")
            
            if not verify_password(data.password, row[2]):
                return AuthResponse(success=False, message="Telefon raqam yoki parol noto'g'ri")
            
            user = UserResponse(id=row[0], phone=row[1], name=row[3], timezone=row[4], language=row[5], created_at=str(row[6]))
            token = create_jwt_token(row[0])
            return AuthResponse(success=True, user=user, token=token)
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT id, phone, password_hash, name, timezone, language, created_at FROM app_users WHERE phone = ?",
            (data.phone,)
        )
        row = await cursor.fetchone()
        
        if not row:
            return AuthResponse(success=False, message="Telefon raqam yoki parol noto'g'ri")
        
        if not verify_password(data.password, row[2]):
            return AuthResponse(success=False, message="Telefon raqam yoki parol noto'g'ri")
        
        user = UserResponse(id=row[0], phone=row[1], name=row[3], timezone=row[4], language=row[5], created_at=str(row[6]))
        token = create_jwt_token(row[0])
        return AuthResponse(success=True, user=user, token=token)


@app.post("/api/auth/send-otp", response_model=OtpResponse)
async def send_otp(data: OtpRequest):
    """Send OTP code to phone number via Unimtx SMS."""
    phone = data.phone.strip()
    
    # Remove any spaces, dashes, parentheses
    phone = phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
    
    # Ensure phone is in E.164 format
    if not phone.startswith('+'):
        # If user typed 998XXXXXXXXX (without +)
        if phone.startswith('998'):
            phone = '+' + phone
        # If user typed 9XXXXXXXX (9 digits, Uzbek mobile)
        elif len(phone) == 9 and phone[0] in '0123456789':
            phone = '+998' + phone
        else:
            phone = '+' + phone
    
    logger.info(f"Send OTP request for phone: {phone}")
    
    if UNIMTX_ENABLED:
        # Use Unimtx OTP API
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{UNIMTX_API_BASE}/?action=otp.send&accessKeyId={UNIMTX_ACCESS_KEY_ID}",
                    json={
                        "to": phone,
                        "channel": "sms",
                        "digits": 6,
                        "ttl": 300,
                    },
                    headers={"Content-Type": "application/json"}
                )
                result = response.json()
                logger.info(f"Unimtx send OTP response for {phone}: code={result.get('code')}, message={result.get('message')}")
                
                if result.get("code") == "0":
                    return OtpResponse(success=True, message="Tasdiqlash kodi yuborildi")
                else:
                    error_msg = result.get("message", "Unknown error")
                    logger.error(f"Unimtx OTP failed: {error_msg}")
                    return OtpResponse(success=False, message=f"SMS yuborishda xatolik: {error_msg}")
        except Exception as e:
            logger.error(f"Unimtx OTP exception: {e}")
            return OtpResponse(success=False, message="SMS xizmatida xatolik yuz berdi")
    else:
        # Fallback: local OTP generation (for development)
        now = datetime.utcnow()
        
        # Clean expired OTPs
        expired_phones = [p for p, v in otp_storage.items() if v["expires"] < now]
        for p in expired_phones:
            del otp_storage[p]
        
        # Rate limiting
        if phone in otp_storage:
            time_since_sent = now - (otp_storage[phone]["expires"] - timedelta(minutes=5))
            if time_since_sent.total_seconds() < 60:
                return OtpResponse(success=False, message="Iltimos, 60 soniya kuting")
        
        otp_code = str(random.randint(100000, 999999))
        otp_storage[phone] = {
            "code": otp_code,
            "expires": now + timedelta(minutes=5),
            "attempts": 0
        }
        logger.info(f"[DEV] OTP for {phone}: {otp_code}")
        return OtpResponse(success=True, message="Tasdiqlash kodi yuborildi")


@app.post("/api/auth/verify-otp", response_model=AuthResponse)
async def verify_otp(data: OtpVerifyRequest):
    """Verify OTP code and complete login/registration."""
    phone = data.phone.strip()
    otp_code = data.otp.strip()
    
    # Remove any spaces, dashes, parentheses
    phone = phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
    
    # Ensure phone is in E.164 format
    if not phone.startswith('+'):
        if phone.startswith('998'):
            phone = '+' + phone
        elif len(phone) == 9 and phone[0] in '0123456789':
            phone = '+998' + phone
        else:
            phone = '+' + phone
    
    logger.info(f"Verify OTP request for phone: {phone}, code: {otp_code}")
    
    # Verify OTP via Unimtx or locally
    otp_valid = False
    
    if UNIMTX_ENABLED:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{UNIMTX_API_BASE}/?action=otp.verify&accessKeyId={UNIMTX_ACCESS_KEY_ID}",
                    json={
                        "to": phone,
                        "code": otp_code,
                    },
                    headers={"Content-Type": "application/json"}
                )
                result = response.json()
                logger.info(f"Unimtx verify OTP response for {phone}: {result}")
                
                if result.get("code") == "0" and result.get("data", {}).get("valid") is True:
                    otp_valid = True
                else:
                    return AuthResponse(success=False, message="Kod noto'g'ri yoki muddati tugagan")
        except Exception as e:
            logger.error(f"Unimtx verify exception: {e}")
            return AuthResponse(success=False, message="Tekshirishda xatolik yuz berdi")
    else:
        # Local verification fallback (for development)
        now = datetime.utcnow()
        
        if phone not in otp_storage:
            return AuthResponse(success=False, message="Kod topilmadi. Qayta urinib ko'ring")
        
        stored = otp_storage[phone]
        
        if stored["expires"] < now:
            del otp_storage[phone]
            return AuthResponse(success=False, message="Kod muddati tugagan. Qayta yuborish tugmasini bosing")
        
        if stored["attempts"] >= 5:
            del otp_storage[phone]
            return AuthResponse(success=False, message="Ko'p marta noto'g'ri kiritildi. Qayta yuborish tugmasini bosing")
        
        if stored["code"] != otp_code:
            otp_storage[phone]["attempts"] += 1
            remaining = 5 - otp_storage[phone]["attempts"]
            return AuthResponse(success=False, message=f"Kod noto'g'ri. {remaining} ta urinish qoldi")
        
        # Valid - clean up
        del otp_storage[phone]
        otp_valid = True
    
    if not otp_valid:
        return AuthResponse(success=False, message="Kod noto'g'ri")
    
    # Handle login or registration
    if data.isLogin:
        # Login flow - verify password and return user
        if USE_TURSO and LIBSQL_AVAILABLE:
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, phone, password_hash, name, timezone, language, created_at FROM app_users WHERE phone = ?",
                    (phone,)
                )
                row = cursor.fetchone()
                conn.close()
                
                if not row:
                    return AuthResponse(success=False, message="Foydalanuvchi topilmadi")
                
                if data.password and not verify_password(data.password, row[2]):
                    return AuthResponse(success=False, message="Parol noto'g'ri")
                
                user = UserResponse(id=row[0], phone=row[1], name=row[3], timezone=row[4], language=row[5], created_at=str(row[6]))
                token = create_jwt_token(row[0])
                return AuthResponse(success=True, user=user, token=token)
        
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cursor = await db.execute(
                "SELECT id, phone, password_hash, name, timezone, language, created_at FROM app_users WHERE phone = ?",
                (phone,)
            )
            row = await cursor.fetchone()
            
            if not row:
                return AuthResponse(success=False, message="Foydalanuvchi topilmadi")
            
            if data.password and not verify_password(data.password, row[2]):
                return AuthResponse(success=False, message="Parol noto'g'ri")
            
            user = UserResponse(id=row[0], phone=row[1], name=row[3], timezone=row[4], language=row[5], created_at=str(row[6]))
            token = create_jwt_token(row[0])
            return AuthResponse(success=True, user=user, token=token)
    else:
        # Registration flow - create new user
        if not data.name or not data.password:
            return AuthResponse(success=False, message="Ism va parol kiritilishi shart")
        
        if USE_TURSO and LIBSQL_AVAILABLE:
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM app_users WHERE phone = ?", (phone,))
                if cursor.fetchone():
                    conn.close()
                    return AuthResponse(success=False, message="Telefon raqam allaqachon ro'yxatdan o'tgan")
                
                password_hash = hash_password(data.password)
                cursor.execute(
                    "INSERT INTO app_users (phone, password_hash, name) VALUES (?, ?, ?)",
                    (phone, password_hash, data.name)
                )
                conn.commit()
                user_id = cursor.lastrowid
                
                cursor.execute(
                    "SELECT id, phone, name, timezone, language, created_at FROM app_users WHERE id = ?",
                    (user_id,)
                )
                row = cursor.fetchone()
                conn.close()
                
                user = UserResponse(id=row[0], phone=row[1], name=row[2], timezone=row[3], language=row[4], created_at=str(row[5]))
                token = create_jwt_token(user_id)
                return AuthResponse(success=True, user=user, token=token)
        
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cursor = await db.execute("SELECT id FROM app_users WHERE phone = ?", (phone,))
            if await cursor.fetchone():
                return AuthResponse(success=False, message="Telefon raqam allaqachon ro'yxatdan o'tgan")
            
            password_hash = hash_password(data.password)
            cursor = await db.execute(
                "INSERT INTO app_users (phone, password_hash, name) VALUES (?, ?, ?)",
                (phone, password_hash, data.name)
            )
            await db.commit()
            user_id = cursor.lastrowid
            
            cursor = await db.execute(
                "SELECT id, phone, name, timezone, language, created_at FROM app_users WHERE id = ?",
                (user_id,)
            )
            row = await cursor.fetchone()
            
            user = UserResponse(id=row[0], phone=row[1], name=row[2], timezone=row[3], language=row[4], created_at=str(row[5]))
            token = create_jwt_token(user_id)
            return AuthResponse(success=True, user=user, token=token)


@app.get("/api/auth/me")
async def get_me(user_id: int = Depends(get_current_user)):
    """Get current user info."""
    if USE_TURSO and LIBSQL_AVAILABLE:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, phone, name, timezone, language, created_at FROM app_users WHERE id = ?",
                (user_id,)
            )
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                raise HTTPException(status_code=404, detail="User not found")
            
            return {"user": UserResponse(id=row[0], phone=row[1], name=row[2], timezone=row[3], language=row[4], created_at=str(row[5]))}
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT id, phone, name, timezone, language, created_at FROM app_users WHERE id = ?",
            (user_id,)
        )
        row = await cursor.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {"user": UserResponse(id=row[0], phone=row[1], name=row[2], timezone=row[3], language=row[4], created_at=str(row[5]))}


# ===== Voice Endpoint =====
@app.post("/api/voice/parse", response_model=VoiceParseResponse)
async def parse_voice(
    audio: UploadFile = File(...),
    language: str = "uz",
    user_id: int = Depends(get_current_user)
):
    """
    Upload voice audio, transcribe it, and parse reminders using AI.
    Returns transcription and extracted reminders.
    """
    # Get user timezone
    user_timezone = DEFAULT_TIMEZONE
    if USE_TURSO and LIBSQL_AVAILABLE:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT timezone FROM app_users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            if row:
                user_timezone = row[0]
            conn.close()
    else:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cursor = await db.execute("SELECT timezone FROM app_users WHERE id = ?", (user_id,))
            row = await cursor.fetchone()
            if row:
                user_timezone = row[0]
    
    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as tmp:
        content = await audio.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        # Transcribe audio
        transcription = await transcribe_audio_elevenlabs(tmp_path, language)
        
        if not transcription:
            return VoiceParseResponse(success=False, message="Ovozni aniqlash imkoni bo'lmadi")
        
        # Parse with Gemini
        reminders = await parse_with_gemini(transcription, user_timezone)
        
        return VoiceParseResponse(
            success=True,
            transcription=transcription,
            reminders=reminders
        )
    finally:
        # Cleanup temp file
        os.unlink(tmp_path)


# ===== Reminder Endpoints =====
@app.get("/api/reminders")
async def get_reminders(
    status: Optional[str] = None,
    user_id: int = Depends(get_current_user)
):
    """Get all reminders for current user."""
    if USE_TURSO and LIBSQL_AVAILABLE:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            if status:
                cursor.execute(
                    """
                    SELECT id, user_id, task_text, notes, location, scheduled_time_utc, 
                           user_timezone, status, recurrence_type, recurrence_time, created_at
                    FROM app_reminders
                    WHERE user_id = ? AND status = ?
                    ORDER BY scheduled_time_utc DESC
                    """,
                    (user_id, status)
                )
            else:
                cursor.execute(
                    """
                    SELECT id, user_id, task_text, notes, location, scheduled_time_utc, 
                           user_timezone, status, recurrence_type, recurrence_time, created_at
                    FROM app_reminders
                    WHERE user_id = ?
                    ORDER BY scheduled_time_utc DESC
                    """,
                    (user_id,)
                )
            rows = cursor.fetchall()
            reminders = rows_to_dicts(cursor, rows)
            conn.close()
            return {"success": True, "reminders": reminders}
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        if status:
            cursor = await db.execute(
                """
                SELECT id, user_id, task_text, notes, location, scheduled_time_utc, 
                       user_timezone, status, recurrence_type, recurrence_time, created_at
                FROM app_reminders
                WHERE user_id = ? AND status = ?
                ORDER BY scheduled_time_utc DESC
                """,
                (user_id, status)
            )
        else:
            cursor = await db.execute(
                """
                SELECT id, user_id, task_text, notes, location, scheduled_time_utc, 
                       user_timezone, status, recurrence_type, recurrence_time, created_at
                FROM app_reminders
                WHERE user_id = ?
                ORDER BY scheduled_time_utc DESC
                """,
                (user_id,)
            )
        
        rows = await cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        reminders = [dict(zip(columns, row)) for row in rows]
        
        return {"success": True, "reminders": reminders}


@app.post("/api/reminders")
async def create_reminder(
    data: ReminderCreate,
    user_id: int = Depends(get_current_user)
):
    """Create a new reminder."""
    if USE_TURSO and LIBSQL_AVAILABLE:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT timezone FROM app_users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            user_timezone = row[0] if row else DEFAULT_TIMEZONE
            
            cursor.execute(
                """
                INSERT INTO app_reminders (user_id, task_text, notes, location, scheduled_time_utc, 
                                           user_timezone, recurrence_type, recurrence_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, data.task_text, data.notes, data.location, data.scheduled_time,
                 user_timezone, data.recurrence_type, data.recurrence_time)
            )
            conn.commit()
            reminder_id = cursor.lastrowid
            
            cursor.execute(
                """
                SELECT id, user_id, task_text, notes, location, scheduled_time_utc, 
                       user_timezone, status, recurrence_type, recurrence_time, created_at
                FROM app_reminders WHERE id = ?
                """,
                (reminder_id,)
            )
            row = cursor.fetchone()
            reminder = row_to_dict(cursor, row)
            conn.close()
            
            return {"success": True, "reminder": reminder}
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("SELECT timezone FROM app_users WHERE id = ?", (user_id,))
        row = await cursor.fetchone()
        user_timezone = row[0] if row else DEFAULT_TIMEZONE
        
        cursor = await db.execute(
            """
            INSERT INTO app_reminders (user_id, task_text, notes, location, scheduled_time_utc, 
                                       user_timezone, recurrence_type, recurrence_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, data.task_text, data.notes, data.location, data.scheduled_time,
             user_timezone, data.recurrence_type, data.recurrence_time)
        )
        await db.commit()
        reminder_id = cursor.lastrowid
        
        cursor = await db.execute(
            """
            SELECT id, user_id, task_text, notes, location, scheduled_time_utc, 
                   user_timezone, status, recurrence_type, recurrence_time, created_at
            FROM app_reminders WHERE id = ?
            """,
            (reminder_id,)
        )
        row = await cursor.fetchone()
        columns = [desc[0] for desc in cursor.description]
        reminder = dict(zip(columns, row))
        
        return {"success": True, "reminder": reminder}


@app.post("/api/reminders/voice")
async def create_reminder_from_voice(
    audio: UploadFile = File(...),
    language: str = "uz",
    user_id: int = Depends(get_current_user)
):
    """
    Create reminders from voice input.
    Transcribes audio, parses with AI, and creates all extracted reminders.
    """
    # Get user timezone
    user_timezone = DEFAULT_TIMEZONE
    if USE_TURSO and LIBSQL_AVAILABLE:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT timezone FROM app_users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            if row:
                user_timezone = row[0]
            conn.close()
    else:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cursor = await db.execute("SELECT timezone FROM app_users WHERE id = ?", (user_id,))
            row = await cursor.fetchone()
            if row:
                user_timezone = row[0]
    
    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as tmp:
        content = await audio.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        # Transcribe audio
        transcription = await transcribe_audio_elevenlabs(tmp_path, language)
        
        if not transcription:
            return {"success": False, "message": "Ovozni aniqlash imkoni bo'lmadi"}
        
        # Parse with Gemini
        parsed_reminders = await parse_with_gemini(transcription, user_timezone)
        
        if not parsed_reminders:
            return {
                "success": False,
                "transcription": transcription,
                "message": "Eslatma topilmadi. Iltimos, qaytadan urinib ko'ring."
            }
        
        # Create all reminders
        created_reminders = []
        for r in parsed_reminders:
            # Use original transcription as notes if no specific notes provided
            notes = r.get('notes') or transcription
            
            reminder_data = ReminderCreate(
                task_text=r.get('task', ''),
                scheduled_time=r.get('time_utc', ''),
                notes=notes,
                location=r.get('location'),
                recurrence_type=r.get('recurrence_type'),
                recurrence_time=r.get('recurrence_time')
            )
            
            result = await create_reminder(reminder_data, user_id)
            if result.get('success'):
                created_reminders.append(result['reminder'])
        
        return {
            "success": True,
            "transcription": transcription,
            "reminders": created_reminders
        }
    finally:
        os.unlink(tmp_path)


@app.patch("/api/reminders/{reminder_id}/status")
async def update_reminder_status(
    reminder_id: int,
    status: str = Body(..., embed=True),
    user_id: int = Depends(get_current_user)
):
    """Update reminder status."""
    if USE_TURSO and LIBSQL_AVAILABLE:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM app_reminders WHERE id = ? AND user_id = ?", (reminder_id, user_id))
            if not cursor.fetchone():
                conn.close()
                raise HTTPException(status_code=404, detail="Reminder not found")
            
            cursor.execute(
                "UPDATE app_reminders SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, reminder_id)
            )
            conn.commit()
            conn.close()
            return {"success": True, "message": "Status updated"}
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("SELECT id FROM app_reminders WHERE id = ? AND user_id = ?", (reminder_id, user_id))
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="Reminder not found")
        
        await db.execute(
            "UPDATE app_reminders SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (status, reminder_id)
        )
        await db.commit()
        return {"success": True, "message": "Status updated"}


@app.delete("/api/reminders/{reminder_id}")
async def delete_reminder(reminder_id: int, user_id: int = Depends(get_current_user)):
    """Delete a reminder."""
    if USE_TURSO and LIBSQL_AVAILABLE:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM app_reminders WHERE id = ? AND user_id = ?", (reminder_id, user_id))
            if not cursor.fetchone():
                conn.close()
                raise HTTPException(status_code=404, detail="Reminder not found")
            
            cursor.execute("DELETE FROM app_reminders WHERE id = ?", (reminder_id,))
            conn.commit()
            conn.close()
            return {"success": True, "message": "Reminder deleted"}
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("SELECT id FROM app_reminders WHERE id = ? AND user_id = ?", (reminder_id, user_id))
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="Reminder not found")
        
        await db.execute("DELETE FROM app_reminders WHERE id = ?", (reminder_id,))
        await db.commit()
        return {"success": True, "message": "Reminder deleted"}


# ===== User Endpoints =====
@app.patch("/api/user/profile")
async def update_profile(data: ProfileUpdate, user_id: int = Depends(get_current_user)):
    """Update user profile."""
    updates = []
    params = []
    
    if data.name:
        updates.append("name = ?")
        params.append(data.name)
    if data.timezone:
        updates.append("timezone = ?")
        params.append(data.timezone)
    if data.fcm_token:
        updates.append("fcm_token = ?")
        params.append(data.fcm_token)
    
    if not updates:
        return {"success": True, "message": "No changes"}
    
    updates.append("updated_at = CURRENT_TIMESTAMP")
    params.append(user_id)
    
    if USE_TURSO and LIBSQL_AVAILABLE:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE app_users SET {', '.join(updates)} WHERE id = ?", params)
            conn.commit()
            conn.close()
            return {"success": True, "message": "Profile updated"}
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(f"UPDATE app_users SET {', '.join(updates)} WHERE id = ?", params)
        await db.commit()
        return {"success": True, "message": "Profile updated"}


@app.post("/api/user/fcm-token")
async def update_fcm_token(data: FCMTokenUpdate, user_id: int = Depends(get_current_user)):
    """Update user's FCM token for push notifications."""
    if USE_TURSO and LIBSQL_AVAILABLE:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE app_users SET fcm_token = ? WHERE id = ?", (data.fcm_token, user_id))
            conn.commit()
            conn.close()
            return {"success": True}
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("UPDATE app_users SET fcm_token = ? WHERE id = ?", (data.fcm_token, user_id))
        await db.commit()
        return {"success": True}


# ===== Admin Panel =====

def verify_admin(password: str = Query(...)):
    """Verify admin password from query param."""
    if password != ADMIN_PASSWORD:
        raise HTTPException(status_code=403, detail="Invalid admin password")
    return True


@app.get("/admin/api/stats")
async def admin_stats(authorized: bool = Depends(verify_admin)):
    """Get dashboard stats."""
    stats = {
        "total_users": 0, "total_reminders": 0, "pending_reminders": 0,
        "done_reminders": 0, "today_reminders": 0, "today_users": 0,
        "users": [], "recent_reminders": []
    }
    
    queries = {
        "total_users": "SELECT COUNT(*) FROM app_users",
        "total_reminders": "SELECT COUNT(*) FROM app_reminders",
        "pending_reminders": "SELECT COUNT(*) FROM app_reminders WHERE status = 'pending'",
        "done_reminders": "SELECT COUNT(*) FROM app_reminders WHERE status = 'done'",
        "today_reminders": "SELECT COUNT(*) FROM app_reminders WHERE DATE(created_at) = DATE('now')",
        "today_users": "SELECT COUNT(*) FROM app_users WHERE DATE(created_at) = DATE('now')",
    }
    
    users_query = """
        SELECT u.id, u.phone, u.name, u.timezone, u.language, u.created_at,
            (SELECT COUNT(*) FROM app_reminders WHERE user_id = u.id) as reminder_count,
            (SELECT COUNT(*) FROM app_reminders WHERE user_id = u.id AND status = 'pending') as pending_count
        FROM app_users u ORDER BY u.created_at DESC
    """
    
    reminders_query = """
        SELECT r.id, r.task_text, r.status, r.scheduled_time_utc, r.created_at,
            r.recurrence_type, u.name, u.phone
        FROM app_reminders r
        JOIN app_users u ON r.user_id = u.id
        ORDER BY r.created_at DESC LIMIT 50
    """
    
    if USE_TURSO and LIBSQL_AVAILABLE:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            for key, q in queries.items():
                cursor.execute(q)
                row = cursor.fetchone()
                stats[key] = row[0] if row else 0
            
            cursor.execute(users_query)
            for row in cursor.fetchall():
                stats["users"].append({
                    "id": row[0], "phone": row[1], "name": row[2],
                    "timezone": row[3], "language": row[4], "created_at": str(row[5]),
                    "reminder_count": row[6], "pending_count": row[7]
                })
            
            cursor.execute(reminders_query)
            for row in cursor.fetchall():
                stats["recent_reminders"].append({
                    "id": row[0], "task_text": row[1], "status": row[2],
                    "scheduled_time": str(row[3]), "created_at": str(row[4]),
                    "recurrence": row[5], "user_name": row[6], "user_phone": row[7]
                })
            conn.close()
    else:
        import aiosqlite as aiosqlite_mod
        async with aiosqlite_mod.connect(DATABASE_PATH) as db:
            for key, q in queries.items():
                cursor = await db.execute(q)
                row = await cursor.fetchone()
                stats[key] = row[0] if row else 0
            
            cursor = await db.execute(users_query)
            for row in await cursor.fetchall():
                stats["users"].append({
                    "id": row[0], "phone": row[1], "name": row[2],
                    "timezone": row[3], "language": row[4], "created_at": str(row[5]),
                    "reminder_count": row[6], "pending_count": row[7]
                })
            
            cursor = await db.execute(reminders_query)
            for row in await cursor.fetchall():
                stats["recent_reminders"].append({
                    "id": row[0], "task_text": row[1], "status": row[2],
                    "scheduled_time": str(row[3]), "created_at": str(row[4]),
                    "recurrence": row[5], "user_name": row[6], "user_phone": row[7]
                })
    
    return stats


@app.get("/admin/api/user/{user_id}/reminders")
async def admin_user_reminders(user_id: int, authorized: bool = Depends(verify_admin)):
    """Get all reminders for a specific user."""
    query = """
        SELECT id, task_text, notes, location, scheduled_time_utc, status, 
               recurrence_type, created_at
        FROM app_reminders WHERE user_id = ? ORDER BY created_at DESC
    """
    reminders = []
    
    if USE_TURSO and LIBSQL_AVAILABLE:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute(query, (user_id,))
            for row in cursor.fetchall():
                reminders.append({
                    "id": row[0], "task_text": row[1], "notes": row[2],
                    "location": row[3], "scheduled_time": str(row[4]),
                    "status": row[5], "recurrence": row[6], "created_at": str(row[7])
                })
            conn.close()
    else:
        import aiosqlite as aiosqlite_mod
        async with aiosqlite_mod.connect(DATABASE_PATH) as db:
            cursor = await db.execute(query, (user_id,))
            for row in await cursor.fetchall():
                reminders.append({
                    "id": row[0], "task_text": row[1], "notes": row[2],
                    "location": row[3], "scheduled_time": str(row[4]),
                    "status": row[5], "recurrence": row[6], "created_at": str(row[7])
                })
    
    return {"reminders": reminders}


@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard():
    """Serve admin dashboard HTML."""
    return ADMIN_HTML


ADMIN_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Levi Admin Panel</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f172a; color: #e2e8f0; min-height: 100vh; }
.login-container { display: flex; justify-content: center; align-items: center; min-height: 100vh; }
.login-box { background: #1e293b; padding: 40px; border-radius: 16px; width: 360px; text-align: center; box-shadow: 0 20px 60px rgba(0,0,0,0.5); }
.login-box h1 { font-size: 28px; margin-bottom: 8px; }
.login-box p { color: #94a3b8; margin-bottom: 24px; }
.login-box input { width: 100%; padding: 12px 16px; background: #0f172a; border: 1px solid #334155; border-radius: 8px; color: #e2e8f0; font-size: 16px; margin-bottom: 16px; outline: none; }
.login-box input:focus { border-color: #3b82f6; }
.login-box button { width: 100%; padding: 12px; background: #3b82f6; border: none; border-radius: 8px; color: white; font-size: 16px; font-weight: 600; cursor: pointer; }
.login-box button:hover { background: #2563eb; }
.error { color: #ef4444; font-size: 14px; margin-bottom: 12px; display: none; }

.dashboard { display: none; }
.topbar { background: #1e293b; padding: 16px 32px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #334155; }
.topbar h1 { font-size: 22px; }
.topbar .badge { background: #22c55e; color: white; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 600; }
.logout-btn { background: #ef4444; border: none; color: white; padding: 8px 16px; border-radius: 8px; cursor: pointer; font-size: 14px; }
.logout-btn:hover { background: #dc2626; }

.content { padding: 24px 32px; max-width: 1400px; margin: 0 auto; }
.stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 32px; }
.stat-card { background: #1e293b; padding: 24px; border-radius: 12px; border: 1px solid #334155; }
.stat-card .label { color: #94a3b8; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px; }
.stat-card .value { font-size: 36px; font-weight: 700; margin-top: 8px; }
.stat-card .value.blue { color: #3b82f6; }
.stat-card .value.green { color: #22c55e; }
.stat-card .value.yellow { color: #eab308; }
.stat-card .value.red { color: #ef4444; }
.stat-card .value.purple { color: #a855f7; }

.section { margin-bottom: 32px; }
.section h2 { font-size: 20px; margin-bottom: 16px; display: flex; align-items: center; gap: 8px; }
.section h2 .count { background: #334155; padding: 2px 10px; border-radius: 10px; font-size: 14px; color: #94a3b8; }

table { width: 100%; border-collapse: collapse; background: #1e293b; border-radius: 12px; overflow: hidden; }
th { text-align: left; padding: 12px 16px; background: #0f172a; color: #94a3b8; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; }
td { padding: 12px 16px; border-top: 1px solid #334155; font-size: 14px; }
tr:hover td { background: #263044; }
.status { padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: 600; display: inline-block; }
.status.pending { background: #fef3c7; color: #92400e; }
.status.done { background: #d1fae5; color: #065f46; }
.phone { color: #94a3b8; font-family: monospace; }
.clickable { cursor: pointer; color: #3b82f6; }
.clickable:hover { text-decoration: underline; }

.modal-overlay { display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.7); z-index: 100; justify-content: center; align-items: flex-start; padding-top: 60px; }
.modal-overlay.active { display: flex; }
.modal { background: #1e293b; border-radius: 16px; width: 700px; max-height: 80vh; overflow-y: auto; padding: 24px; }
.modal h3 { font-size: 18px; margin-bottom: 16px; }
.modal .close-btn { float: right; background: #334155; border: none; color: #e2e8f0; padding: 6px 12px; border-radius: 6px; cursor: pointer; }
.modal .close-btn:hover { background: #475569; }

.refresh-btn { background: #334155; border: none; color: #e2e8f0; padding: 8px 16px; border-radius: 8px; cursor: pointer; font-size: 14px; }
.refresh-btn:hover { background: #475569; }

@media (max-width: 768px) {
    .content { padding: 16px; }
    .stats-grid { grid-template-columns: repeat(2, 1fr); }
    table { font-size: 12px; }
    th, td { padding: 8px 10px; }
    .modal { width: 95%; }
}
</style>
</head>
<body>

<!-- Login Screen -->
<div class="login-container" id="loginScreen">
  <div class="login-box">
    <h1>🔔 Levi Admin</h1>
    <p>Admin panelga kirish</p>
    <div class="error" id="loginError">Noto'g'ri parol</div>
    <input type="password" id="passwordInput" placeholder="Parolni kiriting..." onkeydown="if(event.key==='Enter')login()">
    <button onclick="login()">Kirish</button>
  </div>
</div>

<!-- Dashboard -->
<div class="dashboard" id="dashboard">
  <div class="topbar">
    <div style="display:flex;align-items:center;gap:12px;">
      <h1>🔔 Levi Admin</h1>
      <span class="badge">LIVE</span>
    </div>
    <div style="display:flex;gap:8px;">
      <button class="refresh-btn" onclick="loadData()">🔄 Yangilash</button>
      <button class="logout-btn" onclick="logout()">Chiqish</button>
    </div>
  </div>

  <div class="content">
    <!-- Stats -->
    <div class="stats-grid">
      <div class="stat-card"><div class="label">Foydalanuvchilar</div><div class="value blue" id="statUsers">-</div></div>
      <div class="stat-card"><div class="label">Jami eslatmalar</div><div class="value purple" id="statReminders">-</div></div>
      <div class="stat-card"><div class="label">Kutilmoqda</div><div class="value yellow" id="statPending">-</div></div>
      <div class="stat-card"><div class="label">Bajarildi</div><div class="value green" id="statDone">-</div></div>
      <div class="stat-card"><div class="label">Bugun eslatmalar</div><div class="value red" id="statToday">-</div></div>
      <div class="stat-card"><div class="label">Bugun yangi users</div><div class="value blue" id="statTodayUsers">-</div></div>
    </div>

    <!-- Users -->
    <div class="section">
      <h2>Foydalanuvchilar <span class="count" id="usersCount">0</span></h2>
      <table>
        <thead><tr><th>ID</th><th>Ism</th><th>Telefon</th><th>Til</th><th>Eslatmalar</th><th>Kutilmoqda</th><th>Ro'yxatdan o'tgan</th></tr></thead>
        <tbody id="usersTable"></tbody>
      </table>
    </div>

    <!-- Recent Reminders -->
    <div class="section">
      <h2>So'nggi eslatmalar <span class="count" id="remindersCount">0</span></h2>
      <table>
        <thead><tr><th>ID</th><th>Foydalanuvchi</th><th>Vazifa</th><th>Holat</th><th>Rejalashtirilgan</th><th>Yaratilgan</th></tr></thead>
        <tbody id="remindersTable"></tbody>
      </table>
    </div>
  </div>
</div>

<!-- User Detail Modal -->
<div class="modal-overlay" id="userModal">
  <div class="modal">
    <button class="close-btn" onclick="closeModal()">✕</button>
    <h3 id="modalTitle">Foydalanuvchi</h3>
    <table>
      <thead><tr><th>Vazifa</th><th>Holat</th><th>Vaqt</th><th>Takrorlanish</th><th>Yaratilgan</th></tr></thead>
      <tbody id="modalReminders"></tbody>
    </table>
  </div>
</div>

<script>
let adminPassword = '';
const API = window.location.origin;

function login() {
  adminPassword = document.getElementById('passwordInput').value;
  fetch(`${API}/admin/api/stats?password=${encodeURIComponent(adminPassword)}`)
    .then(r => { if (!r.ok) throw new Error('bad'); return r.json(); })
    .then(data => {
      localStorage.setItem('levi_admin_pw', adminPassword);
      document.getElementById('loginScreen').style.display = 'none';
      document.getElementById('dashboard').style.display = 'block';
      renderData(data);
    })
    .catch(() => {
      document.getElementById('loginError').style.display = 'block';
    });
}

function logout() {
  localStorage.removeItem('levi_admin_pw');
  adminPassword = '';
  document.getElementById('dashboard').style.display = 'none';
  document.getElementById('loginScreen').style.display = 'flex';
  document.getElementById('passwordInput').value = '';
}

function loadData() {
  fetch(`${API}/admin/api/stats?password=${encodeURIComponent(adminPassword)}`)
    .then(r => r.json())
    .then(renderData)
    .catch(e => console.error('Load failed:', e));
}

function renderData(data) {
  document.getElementById('statUsers').textContent = data.total_users;
  document.getElementById('statReminders').textContent = data.total_reminders;
  document.getElementById('statPending').textContent = data.pending_reminders;
  document.getElementById('statDone').textContent = data.done_reminders;
  document.getElementById('statToday').textContent = data.today_reminders;
  document.getElementById('statTodayUsers').textContent = data.today_users;
  document.getElementById('usersCount').textContent = data.users.length;
  document.getElementById('remindersCount').textContent = data.recent_reminders.length;

  // Users table
  const ut = document.getElementById('usersTable');
  ut.innerHTML = data.users.map(u => `
    <tr>
      <td>${u.id}</td>
      <td class="clickable" onclick="showUser(${u.id}, '${(u.name||'').replace(/'/g,"\\\\'")}')"><strong>${u.name || '-'}</strong></td>
      <td class="phone">${u.phone}</td>
      <td>${u.language || 'uz'}</td>
      <td>${u.reminder_count}</td>
      <td>${u.pending_count}</td>
      <td>${formatDate(u.created_at)}</td>
    </tr>
  `).join('');

  // Reminders table
  const rt = document.getElementById('remindersTable');
  rt.innerHTML = data.recent_reminders.map(r => `
    <tr>
      <td>${r.id}</td>
      <td>${r.user_name || '-'} <span class="phone">${r.user_phone}</span></td>
      <td>${r.task_text}</td>
      <td><span class="status ${r.status}">${r.status === 'done' ? 'Bajarildi' : 'Kutilmoqda'}</span></td>
      <td>${formatDate(r.scheduled_time)}</td>
      <td>${formatDate(r.created_at)}</td>
    </tr>
  `).join('');
}

function showUser(userId, name) {
  document.getElementById('modalTitle').textContent = `${name} — Barcha eslatmalar`;
  document.getElementById('userModal').classList.add('active');
  
  fetch(`${API}/admin/api/user/${userId}/reminders?password=${encodeURIComponent(adminPassword)}`)
    .then(r => r.json())
    .then(data => {
      const tb = document.getElementById('modalReminders');
      tb.innerHTML = data.reminders.map(r => `
        <tr>
          <td>${r.task_text}</td>
          <td><span class="status ${r.status}">${r.status === 'done' ? 'Bajarildi' : 'Kutilmoqda'}</span></td>
          <td>${formatDate(r.scheduled_time)}</td>
          <td>${r.recurrence || '-'}</td>
          <td>${formatDate(r.created_at)}</td>
        </tr>
      `).join('');
    });
}

function closeModal() {
  document.getElementById('userModal').classList.remove('active');
}

function formatDate(d) {
  if (!d || d === 'None') return '-';
  try {
    const dt = new Date(d);
    if (isNaN(dt)) return d;
    return dt.toLocaleString('uz-UZ', { day:'2-digit', month:'2-digit', year:'numeric', hour:'2-digit', minute:'2-digit' });
  } catch { return d; }
}

// Auto-login from stored password
window.addEventListener('DOMContentLoaded', () => {
  const saved = localStorage.getItem('levi_admin_pw');
  if (saved) {
    adminPassword = saved;
    document.getElementById('passwordInput').value = saved;
    login();
  }
});

// Auto-refresh every 30 seconds
setInterval(() => {
  if (adminPassword) loadData();
}, 30000);
</script>
</body>
</html>"""


# ===== Health Check =====
@app.get("/api/health")
async def health_check():
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "features": {
            "turso": USE_TURSO and LIBSQL_AVAILABLE,
            "gemini": gemini_model is not None,
            "elevenlabs": ELEVENLABS_AVAILABLE and bool(ELEVENLABS_API_KEY),
            "fcm": bool(FCM_SERVER_KEY)
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
