"""
Aisha.group speech-to-text transcription service for Uzbek voice messages.
Native Uzbek STT with 90% accuracy including dialects.
"""

import logging
import os
import aiohttp
from typing import Optional

logger = logging.getLogger(__name__)

# Aisha STT API endpoint
AISHA_STT_URL = "https://back.aisha.group/api/v1/stt/post/"


class AishaTranscriber:
    """Handles voice transcription using Aisha.group STT API."""
    
    def __init__(self, api_key: str):
        """
        Initialize Aisha transcriber.
        
        Args:
            api_key: Aisha API key
        """
        if not api_key:
            raise ValueError("Aisha API key is required")
        
        self.api_key = api_key
        logger.info("AishaTranscriber initialized")
    
    async def transcribe_voice(self, file_path: str, language: str = "uz") -> Optional[str]:
        """
        Transcribe voice message using Aisha STT API.
        
        Args:
            file_path: Path to the voice file (OGG format from Telegram).
            language: Language code (uz for Uzbek, ru for Russian, en for English).
        
        Returns:
            Transcribed text or None if transcription fails.
        """
        try:
            logger.info(f"Transcribing with Aisha STT (language={language})...")
            
            # Map language codes
            lang_map = {"uz": "uz", "ru": "ru", "en": "en"}
            lang = lang_map.get(language, "uz")
            
            # Prepare headers
            headers = {
                "x-api-key": self.api_key
            }
            
            # Open and send audio file
            async with aiohttp.ClientSession() as session:
                with open(file_path, 'rb') as audio_file:
                    form_data = aiohttp.FormData()
                    form_data.add_field('audio', audio_file, 
                                       filename=os.path.basename(file_path),
                                       content_type='audio/ogg')
                    form_data.add_field('language', lang)
                    
                    async with session.post(AISHA_STT_URL, headers=headers, data=form_data) as response:
                        response_text = await response.text()
                        
                        if response.status == 200:
                            import json
                            result = json.loads(response_text)
                            
                            # Extract text from response
                            if isinstance(result, dict):
                                transcribed_text = result.get('text', result.get('transcript', ''))
                            else:
                                transcribed_text = str(result)
                            
                            transcribed_text = transcribed_text.strip()
                            logger.info(f"Aisha transcribed: {transcribed_text}")
                            return transcribed_text
                        else:
                            logger.error(f"Aisha API error {response.status}: {response_text}")
                            return None
        
        except Exception as e:
            logger.error(f"Aisha transcription error: {e}")
            return None


# Async wrapper function for compatibility with existing code
async def transcribe_audio(file_path: str, language: str = "uz", api_key: str = None) -> Optional[str]:
    """
    Transcribe audio file using Aisha.
    
    Args:
        file_path: Path to audio file
        language: Language code (uz, ru, en)
        api_key: Aisha API key (if not provided, reads from env)
    
    Returns:
        Transcribed text or None if failed
    """
    if not api_key:
        api_key = os.getenv("AISHA_API_KEY")
    
    if not api_key:
        logger.error("AISHA_API_KEY not found in environment")
        return None
    
    transcriber = AishaTranscriber(api_key)
    return await transcriber.transcribe_voice(file_path, language)
