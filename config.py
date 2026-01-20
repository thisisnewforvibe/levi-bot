"""
Configuration module for the Telegram Reminder Bot.
Loads environment variables and provides configuration constants.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Telegram Bot Token
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN environment variable is required")

# Google Cloud Speech-to-Text
# GOOGLE_APPLICATION_CREDENTIALS should be set in environment
GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", None)

# Gemini AI API Key (for intelligent parsing)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
USE_GEMINI_FALLBACK = bool(GEMINI_API_KEY)  # Enable Gemini if API key is present
ALWAYS_USE_GEMINI = os.getenv("ALWAYS_USE_GEMINI", "false").lower() == "true"  # Use Gemini for ALL requests

# Database configuration
DATABASE_PATH = os.getenv("DATABASE_PATH", "reminders.db")

# Turso (Cloud SQLite) configuration
TURSO_DATABASE_URL = os.getenv("TURSO_DATABASE_URL")  # e.g., libsql://your-db-name.turso.io
TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN")
USE_TURSO = bool(TURSO_DATABASE_URL and TURSO_AUTH_TOKEN)

# Reminder settings
FOLLOW_UP_DELAY_SECONDS = 1800  # 30 minutes after reminder
DEFAULT_SNOOZE_MINUTES = 30

# Timezone (default to Tashkent for Uzbekistan)
DEFAULT_TIMEZONE = os.getenv("TIMEZONE", "Asia/Tashkent")

# Rate limiting
RATE_LIMIT_MESSAGES = int(os.getenv("RATE_LIMIT_MESSAGES", "10"))  # Max messages
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))  # Per minute

# Audio quality settings
MIN_VOICE_DURATION_SECONDS = 1  # Minimum voice message duration
MAX_VOICE_DURATION_SECONDS = 300  # Maximum 5 minutes
MIN_TRANSCRIPTION_LENGTH = 3  # Minimum characters for valid transcription

# Supported languages for transcription (Uzbek and Russian)
SUPPORTED_LANGUAGES = ["uz", "ru"]  # O'zbek, Русский

# Transcription service configuration
TRANSCRIPTION_SERVICE = os.getenv("TRANSCRIPTION_SERVICE", "aisha").lower()  # "aisha", "elevenlabs", "whisper", or "google"
WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "base")  # tiny, base, small, medium, large
USE_GEMINI_CORRECTION = os.getenv("USE_GEMINI_CORRECTION", "false").lower() == "true"  # Post-correct with Gemini

# ElevenLabs API configuration
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

# Aisha API configuration (native Uzbek STT)
AISHA_API_KEY = os.getenv("AISHA_API_KEY")
USE_AISHA = TRANSCRIPTION_SERVICE == "aisha"

# Admin configuration
ADMIN_USER_IDS = [int(id.strip()) for id in os.getenv("ADMIN_USER_IDS", "").split(",") if id.strip()]

# Retry settings
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 1
