"""
ElevenLabs speech-to-text transcription service for Uzbek voice messages.
Provides industry-leading accuracy (15.9% WER) for Uzbek language.
"""

import logging
import os
from typing import Optional
from elevenlabs.client import ElevenLabs

logger = logging.getLogger(__name__)

class ElevenLabsTranscriber:
    """Handles voice transcription using ElevenLabs Scribe API."""
    
    def __init__(self, api_key: str):
        """
        Initialize ElevenLabs transcriber.
        
        Args:
            api_key: ElevenLabs API key
        """
        if not api_key:
            raise ValueError("ElevenLabs API key is required")
        
        self.client = ElevenLabs(api_key=api_key)
        logger.info("ElevenLabsTranscriber initialized")
    
    async def transcribe_voice(self, file_path: str, language: str = "uz") -> Optional[str]:
        """
        Transcribe voice message using ElevenLabs Scribe.
        
        Args:
            file_path: Path to the voice file (OGG format from Telegram).
            language: Expected language code (uz for Uzbek, ru for Russian).
        
        Returns:
            Transcribed text or None if transcription fails.
        """
        try:
            logger.info(f"Transcribing with ElevenLabs Scribe (language={language})...")
            
            # Open audio file
            with open(file_path, 'rb') as audio_file:
                # Language mapping: uz -> uzb, ru -> rus
                # See: https://elevenlabs.io/docs/api-reference/speech-to-text/convert
                language_code = None  # Auto-detect by default
                if language == "uz":
                    language_code = "uzb"  # Uzbek
                elif language == "ru":
                    language_code = "rus"  # Russian
                
                # Call ElevenLabs STT API with correct parameters
                result = self.client.speech_to_text.convert(
                    file=audio_file,
                    model_id="scribe_v2",
                    language_code=language_code
                )
                
                # Extract text from result
                transcribed_text = result.text.strip() if hasattr(result, 'text') else str(result).strip()
                
                logger.info(f"ElevenLabs transcribed: {transcribed_text}")
                return transcribed_text
        
        except Exception as e:
            logger.error(f"ElevenLabs transcription error: {e}")
            return None


# Async wrapper function for compatibility with existing code
async def transcribe_audio(file_path: str, language: str = "uz", api_key: str = None) -> Optional[str]:
    """
    Transcribe audio file using ElevenLabs.
    
    Args:
        file_path: Path to audio file
        language: Language code (uz, ru)
        api_key: ElevenLabs API key (if not provided, reads from env)
    
    Returns:
        Transcribed text or None if failed
    """
    if not api_key:
        api_key = os.getenv("ELEVENLABS_API_KEY")
    
    if not api_key:
        logger.error("ELEVENLABS_API_KEY not found in environment")
        return None
    
    transcriber = ElevenLabsTranscriber(api_key)
    return await transcriber.transcribe_voice(file_path, language)
