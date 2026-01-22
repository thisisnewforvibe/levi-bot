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
from datetime import datetime, timedelta
from typing import Optional, List
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, Header, UploadFile, File, BackgroundTasks, Body
from fastapi.middleware.cors import CORSMiddleware
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
async def transcribe_audio_elevenlabs(file_path: str, language: str = "uz") -> Optional[str]:
    """Transcribe audio using ElevenLabs Scribe."""
    if not ELEVENLABS_AVAILABLE or not ELEVENLABS_API_KEY:
        logger.warning("ElevenLabs not available")
        return None
    
    try:
        client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
        
        with open(file_path, 'rb') as audio_file:
            language_code = "uzb" if language == "uz" else "rus" if language == "ru" else None
            
            result = client.speech_to_text.convert(
                file=audio_file,
                model_id="scribe_v2",
                language_code=language_code
            )
            
            return result.text.strip() if hasattr(result, 'text') else str(result).strip()
    except Exception as e:
        logger.error(f"ElevenLabs transcription error: {e}")
        return None


# ===== Gemini AI Parsing =====
async def parse_with_gemini(text: str, user_timezone: str = DEFAULT_TIMEZONE) -> List[dict]:
    """Use Gemini AI to parse reminder text."""
    if not gemini_model:
        logger.warning("Gemini not available")
        return []
    
    try:
        now_utc = datetime.utcnow()
        
        prompt = f"""You are a smart reminder assistant. Parse the following text and extract reminder tasks.

Current date and time (UTC): {now_utc.strftime('%Y-%m-%d %H:%M')}
User timezone: {user_timezone}

Text: "{text}"

Extract ALL reminders. For each reminder determine:
1. Task description (short, action-oriented)
2. Scheduled time in UTC (ISO format: YYYY-MM-DD HH:MM)
3. Notes/details (items to buy, things to remember)
4. Location (if mentioned)
5. Recurrence type: "daily", "weekly", "weekdays", "monthly", or null
6. Recurrence time (HH:MM in user's timezone)

Time parsing rules:
- "har kuni" = daily, "har hafta" = weekly, "har oy" = monthly
- "ertalab" = 8:00 AM, "kechqurun" = 6:00 PM
- "ertaga" = tomorrow at 9:00 AM
- "5 minut" = 5 minutes from now
- Numbers: "o'n" = 10, "to'qqiz" = 9, "sakkiz" = 8

Return ONLY a JSON array:
[
  {{"task": "task description", "time_utc": "2026-01-22 14:00", "notes": "note text or null", "location": "place or null", "recurrence_type": "daily or null", "recurrence_time": "09:00 or null"}}
]

If not a reminder, return: []
"""
        
        response = gemini_model.generate_content(prompt)
        result_text = response.text.strip()
        
        # Extract JSON
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0].strip()
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0].strip()
        
        reminders = json.loads(result_text)
        return reminders if isinstance(reminders, list) else []
    
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
            reminder_data = ReminderCreate(
                task_text=r.get('task', ''),
                scheduled_time=r.get('time_utc', ''),
                notes=r.get('notes'),
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
