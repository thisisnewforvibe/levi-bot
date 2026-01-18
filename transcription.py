"""
Transcription module using Google Cloud Speech-to-Text API.
Handles voice message to text conversion with support for Uzbek and Russian.
"""

import os
import tempfile
import logging
import asyncio
import subprocess
from typing import Optional, Tuple
from google.cloud import speech
from google.api_core import exceptions as google_exceptions
from config import (
    MIN_TRANSCRIPTION_LENGTH,
    MAX_RETRIES,
    RETRY_DELAY_SECONDS,
)

logger = logging.getLogger(__name__)

# Language codes for Google Cloud Speech-to-Text
LANGUAGE_CODES = {
    'uz': 'uz-UZ',  # Uzbek
    'ru': 'ru-RU',  # Russian
}

# Default language (Russian is more commonly supported)
DEFAULT_LANGUAGE = 'ru-RU'


class TranscriptionError(Exception):
    """Custom exception for transcription errors."""
    pass


class PoorAudioQualityError(TranscriptionError):
    """Raised when audio quality is too poor to transcribe."""
    pass


class AudioTooShortError(TranscriptionError):
    """Raised when audio is too short."""
    pass


def convert_ogg_to_wav(ogg_path: str) -> str:
    """
    Convert OGG audio file to WAV format for Google Cloud Speech.
    Uses pydub with ffmpeg.
    
    Args:
        ogg_path: Path to the OGG file.
    
    Returns:
        Path to the converted WAV file.
    """
    from pydub import AudioSegment
    import shutil
    
    # Set ffmpeg path if available in system
    ffmpeg_path = shutil.which('ffmpeg')
    if ffmpeg_path:
        AudioSegment.converter = ffmpeg_path
        ffprobe_path = shutil.which('ffprobe')
        if ffprobe_path:
            AudioSegment.ffprobe = ffprobe_path
    
    wav_path = ogg_path.replace('.ogg', '.wav')
    
    try:
        # Load OGG and convert to WAV (16kHz mono, 16-bit for speech recognition)
        audio = AudioSegment.from_ogg(ogg_path)
        audio = audio.set_frame_rate(16000).set_channels(1)
        # Export as 16-bit PCM WAV
        audio.export(wav_path, format='wav', parameters=["-acodec", "pcm_s16le"])
        logger.debug(f"Converted {ogg_path} to {wav_path}")
        return wav_path
    except Exception as e:
        logger.error(f"Failed to convert audio: {e}")
        raise TranscriptionError(f"Audio conversion failed: {e}")


async def transcribe_voice_message(
    voice_file_path: str,
    language: Optional[str] = None
) -> Tuple[str, Optional[str]]:
    """
    Transcribe a voice message to text using Google Cloud Speech-to-Text.
    Supports Uzbek and Russian languages.
    
    Args:
        voice_file_path: Path to the voice file (OGG format from Telegram).
        language: Optional language hint (e.g., 'ru', 'uz').
    
    Returns:
        Tuple of (transcribed_text, detected_language).
    
    Raises:
        PoorAudioQualityError: If audio quality is too poor.
        TranscriptionError: If transcription fails after retries.
    """
    last_error = None
    wav_path = None
    
    # Convert OGG to WAV
    try:
        wav_path = convert_ogg_to_wav(voice_file_path)
    except Exception as e:
        raise TranscriptionError(f"Failed to convert audio: {e}")
    
    try:
        # Read the audio file
        with open(wav_path, 'rb') as audio_file:
            content = audio_file.read()
        
        # Initialize the Speech client
        client = speech.SpeechClient()
        
        audio = speech.RecognitionAudio(content=content)
        
        # Determine language code
        if language and language in LANGUAGE_CODES:
            primary_lang = LANGUAGE_CODES[language]
        else:
            primary_lang = DEFAULT_LANGUAGE
        
        # Configure recognition with alternative languages
        # Try both Russian and Uzbek for better recognition
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code=primary_lang,
            alternative_language_codes=['uz-UZ', 'ru-RU'] if primary_lang not in ['uz-UZ', 'ru-RU'] else 
                                        ['ru-RU'] if primary_lang == 'uz-UZ' else ['uz-UZ'],
            enable_automatic_punctuation=True,
            model='default',
            use_enhanced=True,  # Use enhanced model for better accuracy
            # Add speech contexts for common words in Uzbek reminders
            speech_contexts=[
                speech.SpeechContext(
                    phrases=[
                        "minut", "soat", "kun", "hafta", "keyin", "eslat",
                        "o'qish", "shom", "namoz", "dori", "qo'ng'iroq",
                        "telefon", "xabar", "uchrashish", "ertaga", "bugun"
                    ],
                    boost=15.0  # Boost these common words
                )
            ],
        )
        
        for attempt in range(MAX_RETRIES):
            try:
                # Perform the transcription (synchronous, wrapped in asyncio)
                response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: client.recognize(config=config, audio=audio)
                )
                
                # Extract transcription from response
                if not response.results:
                    raise PoorAudioQualityError(
                        "No speech detected in audio"
                    )
                
                transcript_parts = []
                detected_lang = None
                
                for result in response.results:
                    if result.alternatives:
                        transcript_parts.append(result.alternatives[0].transcript)
                        # Get detected language from first result
                        if not detected_lang and hasattr(result, 'language_code'):
                            detected_lang = result.language_code
                
                transcript = ' '.join(transcript_parts).strip()
                
                # Check for poor quality indicators
                if not transcript or len(transcript) < MIN_TRANSCRIPTION_LENGTH:
                    raise PoorAudioQualityError(
                        "Transcription too short - audio may be unclear"
                    )
                
                # Map language code back to short form
                if detected_lang:
                    if 'ru' in detected_lang.lower():
                        detected_lang = 'ru'
                    elif 'uz' in detected_lang.lower():
                        detected_lang = 'uz'
                else:
                    # Default based on primary language
                    detected_lang = 'ru' if 'ru' in primary_lang else 'uz'
                
                logger.info(
                    f"Successfully transcribed voice message "
                    f"(lang={detected_lang}): {transcript[:50]}..."
                )
                return transcript, detected_lang
            
            except google_exceptions.ResourceExhausted as e:
                logger.warning(f"Google Cloud quota exceeded, attempt {attempt + 1}/{MAX_RETRIES}")
                last_error = e
                await asyncio.sleep(RETRY_DELAY_SECONDS * (attempt + 1))
            
            except google_exceptions.ServiceUnavailable as e:
                logger.warning(f"Google Cloud service unavailable, attempt {attempt + 1}/{MAX_RETRIES}")
                last_error = e
                await asyncio.sleep(RETRY_DELAY_SECONDS)
            
            except google_exceptions.InvalidArgument as e:
                logger.error(f"Google Cloud invalid argument: {e}")
                raise TranscriptionError(f"Invalid audio format: {e}")
            
            except PoorAudioQualityError:
                raise
            
            except Exception as e:
                logger.error(f"Unexpected error during transcription: {e}")
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_DELAY_SECONDS)
        
        raise TranscriptionError(f"Failed after {MAX_RETRIES} attempts: {last_error}")
    
    finally:
        # Clean up converted WAV file
        if wav_path and os.path.exists(wav_path):
            os.remove(wav_path)
            logger.debug(f"Cleaned up converted file: {wav_path}")


async def download_and_transcribe(
    bot,
    voice,
    language_hint: Optional[str] = None
) -> Tuple[str, Optional[str]]:
    """
    Download a voice message from Telegram and transcribe it.
    
    Args:
        bot: The Telegram bot instance.
        voice: The Voice object from Telegram.
        language_hint: Optional language code for better transcription.
    
    Returns:
        Tuple of (transcribed_text, detected_language).
    
    Raises:
        AudioTooShortError: If audio is too short.
        PoorAudioQualityError: If audio quality is poor.
        TranscriptionError: If transcription fails.
    """
    from config import MIN_VOICE_DURATION_SECONDS, MAX_VOICE_DURATION_SECONDS
    
    # Check voice duration
    if voice.duration < MIN_VOICE_DURATION_SECONDS:
        raise AudioTooShortError(
            f"Voice message too short ({voice.duration}s). "
            f"Please record at least {MIN_VOICE_DURATION_SECONDS} second(s)."
        )
    
    if voice.duration > MAX_VOICE_DURATION_SECONDS:
        raise TranscriptionError(
            f"Voice message too long ({voice.duration}s). "
            f"Maximum is {MAX_VOICE_DURATION_SECONDS // 60} minutes."
        )
    
    # Create a temporary file to store the voice message
    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as temp_file:
        temp_path = temp_file.name
    
    try:
        # Download the voice file from Telegram
        file = await bot.get_file(voice.file_id)
        await file.download_to_drive(temp_path)
        
        # Check file size (very small files likely have no audio)
        file_size = os.path.getsize(temp_path)
        if file_size < 1000:  # Less than 1KB
            raise PoorAudioQualityError("Audio file too small - may be corrupted")
        
        logger.info(f"Downloaded voice message to {temp_path} ({file_size} bytes)")
        
        # Transcribe the voice message
        transcription, detected_lang = await transcribe_voice_message(
            temp_path,
            language=language_hint
        )
        
        return transcription, detected_lang
    
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_path):
            os.remove(temp_path)
            logger.debug(f"Cleaned up temporary file: {temp_path}")
