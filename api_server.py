"""
FastAPI Backend Server for Levi Mobile App
Provides REST API for reminder management
"""

import os
import jwt
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import aiosqlite

# Configuration
DATABASE_PATH = os.environ.get('DATABASE_PATH', 'reminders.db')
JWT_SECRET = os.environ.get('JWT_SECRET', 'levi-app-secret-key-change-in-production')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24 * 30  # 30 days

app = FastAPI(title="Levi API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your app's domain
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


class ReminderStatusUpdate(BaseModel):
    status: str


class ReminderReschedule(BaseModel):
    scheduled_time: str


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    timezone: Optional[str] = None


class PasswordUpdate(BaseModel):
    current_password: str
    new_password: str


# ===== Database Initialization =====
async def init_app_database():
    """Initialize app-specific tables (users with passwords)."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS app_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                name TEXT NOT NULL,
                timezone TEXT DEFAULT 'Asia/Tashkent',
                language TEXT DEFAULT 'uz',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS app_reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                task_text TEXT NOT NULL,
                scheduled_time_utc TIMESTAMP NOT NULL,
                user_timezone TEXT DEFAULT 'Asia/Tashkent',
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES app_users(id)
            )
        """)
        
        await db.commit()


@app.on_event("startup")
async def startup():
    await init_app_database()


# ===== Utility Functions =====
def hash_password(password: str) -> str:
    """Hash password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    """Verify password against hash."""
    return hash_password(password) == password_hash


def create_jwt_token(user_id: int) -> str:
    """Create JWT token for user."""
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_jwt_token(token: str) -> Optional[int]:
    """Decode JWT token and return user_id."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload.get('user_id')
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


async def get_current_user(authorization: Optional[str] = Header(None)) -> int:
    """Dependency to get current user from JWT token."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    
    if not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    
    token = authorization[7:]
    user_id = decode_jwt_token(token)
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return user_id


# ===== Auth Endpoints =====
@app.post("/api/auth/register", response_model=AuthResponse)
async def register(data: RegisterRequest):
    """Register a new user."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Check if phone already exists
        cursor = await db.execute(
            "SELECT id FROM app_users WHERE phone = ?",
            (data.phone,)
        )
        if await cursor.fetchone():
            return AuthResponse(success=False, message="Telefon raqam allaqachon ro'yxatdan o'tgan")
        
        # Create user
        password_hash = hash_password(data.password)
        cursor = await db.execute(
            """
            INSERT INTO app_users (phone, password_hash, name)
            VALUES (?, ?, ?)
            """,
            (data.phone, password_hash, data.name)
        )
        await db.commit()
        user_id = cursor.lastrowid
        
        # Get user data
        cursor = await db.execute(
            "SELECT id, phone, name, timezone, language, created_at FROM app_users WHERE id = ?",
            (user_id,)
        )
        row = await cursor.fetchone()
        
        user = UserResponse(
            id=row[0],
            phone=row[1],
            name=row[2],
            timezone=row[3],
            language=row[4],
            created_at=row[5]
        )
        
        token = create_jwt_token(user_id)
        
        return AuthResponse(success=True, user=user, token=token)


@app.post("/api/auth/login", response_model=AuthResponse)
async def login(data: LoginRequest):
    """Login user."""
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
        
        user = UserResponse(
            id=row[0],
            phone=row[1],
            name=row[3],
            timezone=row[4],
            language=row[5],
            created_at=row[6]
        )
        
        token = create_jwt_token(row[0])
        
        return AuthResponse(success=True, user=user, token=token)


@app.get("/api/auth/me")
async def get_me(user_id: int = Depends(get_current_user)):
    """Get current user info."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT id, phone, name, timezone, language, created_at FROM app_users WHERE id = ?",
            (user_id,)
        )
        row = await cursor.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "user": UserResponse(
                id=row[0],
                phone=row[1],
                name=row[2],
                timezone=row[3],
                language=row[4],
                created_at=row[5]
            )
        }


# ===== Reminder Endpoints =====
@app.get("/api/reminders")
async def get_reminders(status: Optional[str] = None, user_id: int = Depends(get_current_user)):
    """Get all reminders for current user."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        if status:
            cursor = await db.execute(
                """
                SELECT id, user_id, task_text, scheduled_time_utc, user_timezone, status, created_at
                FROM app_reminders
                WHERE user_id = ? AND status = ?
                ORDER BY scheduled_time_utc DESC
                """,
                (user_id, status)
            )
        else:
            cursor = await db.execute(
                """
                SELECT id, user_id, task_text, scheduled_time_utc, user_timezone, status, created_at
                FROM app_reminders
                WHERE user_id = ?
                ORDER BY scheduled_time_utc DESC
                """,
                (user_id,)
            )
        
        rows = await cursor.fetchall()
        reminders = [
            {
                "id": row[0],
                "user_id": row[1],
                "task_text": row[2],
                "scheduled_time_utc": row[3],
                "user_timezone": row[4],
                "status": row[5],
                "created_at": row[6]
            }
            for row in rows
        ]
        
        return {"success": True, "reminders": reminders}


@app.get("/api/reminders/{reminder_id}")
async def get_reminder(reminder_id: int, user_id: int = Depends(get_current_user)):
    """Get a specific reminder."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            """
            SELECT id, user_id, task_text, scheduled_time_utc, user_timezone, status, created_at
            FROM app_reminders
            WHERE id = ? AND user_id = ?
            """,
            (reminder_id, user_id)
        )
        row = await cursor.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Reminder not found")
        
        return {
            "success": True,
            "reminder": {
                "id": row[0],
                "user_id": row[1],
                "task_text": row[2],
                "scheduled_time_utc": row[3],
                "user_timezone": row[4],
                "status": row[5],
                "created_at": row[6]
            }
        }


@app.post("/api/reminders")
async def create_reminder(data: ReminderCreate, user_id: int = Depends(get_current_user)):
    """Create a new reminder."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Get user timezone
        cursor = await db.execute(
            "SELECT timezone FROM app_users WHERE id = ?",
            (user_id,)
        )
        row = await cursor.fetchone()
        user_timezone = row[0] if row else 'Asia/Tashkent'
        
        cursor = await db.execute(
            """
            INSERT INTO app_reminders (user_id, task_text, scheduled_time_utc, user_timezone)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, data.task_text, data.scheduled_time, user_timezone)
        )
        await db.commit()
        reminder_id = cursor.lastrowid
        
        cursor = await db.execute(
            """
            SELECT id, user_id, task_text, scheduled_time_utc, user_timezone, status, created_at
            FROM app_reminders
            WHERE id = ?
            """,
            (reminder_id,)
        )
        row = await cursor.fetchone()
        
        return {
            "success": True,
            "reminder": {
                "id": row[0],
                "user_id": row[1],
                "task_text": row[2],
                "scheduled_time_utc": row[3],
                "user_timezone": row[4],
                "status": row[5],
                "created_at": row[6]
            }
        }


@app.patch("/api/reminders/{reminder_id}/status")
async def update_reminder_status(
    reminder_id: int,
    data: ReminderStatusUpdate,
    user_id: int = Depends(get_current_user)
):
    """Update reminder status."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Verify ownership
        cursor = await db.execute(
            "SELECT id FROM app_reminders WHERE id = ? AND user_id = ?",
            (reminder_id, user_id)
        )
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="Reminder not found")
        
        await db.execute(
            """
            UPDATE app_reminders
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (data.status, reminder_id)
        )
        await db.commit()
        
        return {"success": True, "message": "Status updated"}


@app.patch("/api/reminders/{reminder_id}/reschedule")
async def reschedule_reminder(
    reminder_id: int,
    data: ReminderReschedule,
    user_id: int = Depends(get_current_user)
):
    """Reschedule a reminder."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Verify ownership
        cursor = await db.execute(
            "SELECT id FROM app_reminders WHERE id = ? AND user_id = ?",
            (reminder_id, user_id)
        )
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="Reminder not found")
        
        await db.execute(
            """
            UPDATE app_reminders
            SET scheduled_time_utc = ?, status = 'pending', updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (data.scheduled_time, reminder_id)
        )
        await db.commit()
        
        return {"success": True, "message": "Reminder rescheduled"}


@app.delete("/api/reminders/{reminder_id}")
async def delete_reminder(reminder_id: int, user_id: int = Depends(get_current_user)):
    """Delete a reminder."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Verify ownership
        cursor = await db.execute(
            "SELECT id FROM app_reminders WHERE id = ? AND user_id = ?",
            (reminder_id, user_id)
        )
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="Reminder not found")
        
        await db.execute("DELETE FROM app_reminders WHERE id = ?", (reminder_id,))
        await db.commit()
        
        return {"success": True, "message": "Reminder deleted"}


# ===== User Endpoints =====
@app.patch("/api/user/profile")
async def update_profile(data: ProfileUpdate, user_id: int = Depends(get_current_user)):
    """Update user profile."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        updates = []
        params = []
        
        if data.name:
            updates.append("name = ?")
            params.append(data.name)
        
        if data.timezone:
            updates.append("timezone = ?")
            params.append(data.timezone)
        
        if updates:
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(user_id)
            
            await db.execute(
                f"UPDATE app_users SET {', '.join(updates)} WHERE id = ?",
                params
            )
            await db.commit()
        
        return {"success": True, "message": "Profile updated"}


@app.patch("/api/user/password")
async def update_password(data: PasswordUpdate, user_id: int = Depends(get_current_user)):
    """Update user password."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Verify current password
        cursor = await db.execute(
            "SELECT password_hash FROM app_users WHERE id = ?",
            (user_id,)
        )
        row = await cursor.fetchone()
        
        if not row or not verify_password(data.current_password, row[0]):
            raise HTTPException(status_code=400, detail="Current password is incorrect")
        
        # Update password
        new_hash = hash_password(data.new_password)
        await db.execute(
            "UPDATE app_users SET password_hash = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (new_hash, user_id)
        )
        await db.commit()
        
        return {"success": True, "message": "Password updated"}


# Health check
@app.get("/api/health")
async def health_check():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
