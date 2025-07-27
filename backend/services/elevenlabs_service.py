# backend/services/elevenlabs_service.py
import httpx
import asyncio
import io
import base64
from typing import Dict, List, Optional, Any, BinaryIO
from datetime import datetime
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential
from models.configs import Settings
import os

logger = structlog.get_logger()


class ElevenLabsService:
    """Service for ElevenLabs Speech-to-Text and Text-to-Speech operations"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.api_key = os.getenv("ELEVENLABS_API_KEY")
        self.base_url = "https://api.elevenlabs.io/v1"
        
        # Default voice settings
        self.default_voice_id = "21m00Tcm4TlvDq8ikWAM"  # Rachel voice
        self.voice_settings = {
            "stability": 0.75,
            "similarity_boost": 0.75,
            "style": 0.0,
            "use_speaker_boost": True
        }

        # HTTP client configuration
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            headers={
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": self.api_key
            }
        )

        if not self.api_key:
            logger.warning("⚠️ ElevenLabs API key not found. Voice features will be disabled.")
        else:
            logger.info("✅ ElevenLabs service initialized")

    async def health_check(self) -> Dict[str, Any]:
        """Check ElevenLabs service health"""
        try:
            if not self.api_key:
                return {
                    "status": "disabled",
                    "message": "API key not configured",
                    "last_check": datetime.now()
                }

            start_time = datetime.now()
            
            # Test API connectivity by getting user info
            response = await self.client.get(f"{self.base_url}/user")
            response_time = (datetime.now() - start_time).total_seconds() * 1000

            if response.status_code == 200:
                user_data = response.json()
                return {
                    "status": "healthy",
                    "response_time": response_time,
                    "last_check": datetime.now(),
                    "character_count": user_data.get("subscription", {}).get("character_count", 0),
                    "character_limit": user_data.get("subscription", {}).get("character_limit", 0)
                }
            else:
                return {
                    "status f"HTTP {response.status_code}"
                }

        except Exception as e:
            logger.error("❌ ElevenLabs health check failed", error=str(e))
            return {
                "status": "unhealthy",
                "last_check": datetime.now(),
                "error": str(e)
            }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1,
    async def text_to_speech(self, text: str, voice_id: Optionalvoice_settings: Optional[Dict] = None) -> bytes:
        """Convert text to speech using ElevenLabs TTS"""
        if not self.api_key:
            raise Exception("ElevenLabs API key=len(text), 
                       voice_id=voice_id or self.default_voice_id)

            # Use provided voice_id or default
            selected_voice_id = voice_id or self.default_voice_id
            
            # Use provided voiceolingual_v1",
                "voice_settings": settings
            }

            # Make TTS request
            response = await self.client.post(
                f"{self.base_url}/text{"Accept": "audio/mpeg"}
            )

            response
            audio 
                       audio_size=len(audio_data))
            
            return audio_data

        .error("❌ Text-to-speech conversion failed", error=str(e))
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=8))
    async def speech_to_text(self, audio_data: bytes, 
                           model_id: str = "eleven_multilingual_v2") -> Dict[str, Any]:
        """Convert speech to text using ElevenLabs STT""":
            raise Exception("Ele to text with ElevenLabs STT", 
                       audio_size=len(audio_data))

            # Prepare multipart form data for ElevenLabs STT
            files = {
                "audio": ("audio.mp3", io.BytesIO(audio_data), "audio/mpeg")
            }
            
            data = {
                "model_id": model_id,
                "language_code": "en",  # Can be made configurable
                "response_format": "json"
            }

            # Use ElevenLabs STT endpoint
            response = await self.api_key,
                    "Accept": "application/json"
                }
            )

            if response.status_code == 200✅ ElevenLabs speech-to-text conversion completed")
                return {
                    "text": result.get("text", "abs typically has high confidence
                    "language": result.get("detected_language", "en"),
                    "duration": result.get("duration_seconds", 0.0),
                    "alignment": result_code == 422:
                # Handle validation errors
                error_detail = response.json()
                
                    "text": "[Invali    "confidence": 0.0 0.0,
                    "error": f"Validation error: {error_detail}"
                }
            else:
                logger {
                    "text": "[Speech recognition unavailable]",
                    "confidence": 0.0,
                    "language": "en",
                    "duration": 0.0,
                    .status_code}"
                }

        except Exception as e:(e))
            return {
                "text": "[Speech recognition failed]",
                "confidence": 0.0,
                "language": "en",
                "duration"error": str(e)
            }

    async def get_available_voices(self) -> List[Dict[str, Any]]:
        """Get list of available voices"""
        if not self.api_key:
            return []

        try:
            response = await self.client.get(f"{self.base_url}/voices")
            response.raise_for_status()
            
            voices_data = response.json()
            voices = []
            
            for voice in voices_data.get("voices", []):
                voices.append({
                    "voice_id": voice.get("voice_id"),
                    "name": voice.get("name"),
                    "category": voice.get("category"),
                    "description
                    "available_for_tiers
                })
            
            logger.info("✅ Retrieved available voices", count=len(voices))
            return voices__response: str, 
                                               voice_id: Optional[str] = None) -> Dict[str, Any]:
        """Create a complete voice both text and audio"""
        try text
            audio_data = await voice_id)
            
            # Convert audio to base64 for JSON response
            audio_base64 = base64.b64encode(audio_data).decode('utf- {
                    "data": audio_base64,
                    "format": "mp3",
                    "size": len(audio_data)
                },
                "voice_id": voice_id or self.default_voice_id, response", error=str(e))
            return {
                "text": text_response,
                "audio": None,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def process_voice_input(self, audio_data: bytes) -> Dict[str, Any]:
        """Process voice input and return transcribed text"""
        try:
            # Convert speech to text using ElevenLabs STT
            stt_result = await self.speech_to_text(audio_data": True,
                "transcription": stt_result.get("text", ""),
                "duration": stt_result.get("duration", 0.0),
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error("❌ Faile(self, user_preferences: Dict[str, Any]) -> Dict[str, Any]:
        ized voice settings base Default settings
        settings":
            settings["similarity_boost
        return settings

    async def cleanup(self):
        """Cleanup resources"""
                "text": text_response,
                "audio": {
                    "data": audio_base64,
                    "format": "mp3",
                    "size": len(audio_data)
                },
                "voice_id": voice_id or self.default_voice_id,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error("❌ Failed to create voice response", error=str(e))
            return {
                "text": text_response,
                "audio": None,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def process_voice_input(self, audio_data: bytes) -> Dict[str, Any]:
        """Process voice input and return transcribed text"""
        try:
            # Convert speech to text
            stt_result = await self.speech_to_text(audio_data)
            
            return {
                "success": True,
                "transcription": stt_result.get("text", ""),
                "confidence": stt_result.get("confidence", 0.0),": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error("❌ Failed to process voice input", error=str(e))
            return {
                "success": False,
                "transcription": "",
                "confidence"error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def get_voice_settings_for_user(self, user_preferences: Dict[str, Any]) -> Dict[str, Any]:
        """Get optimized voice settings based on user preferences"""
        # Default settings
        settings = self.voice_settings.copy()
        
        # Adjust based on user preferences
        if user_preferences.get("voice_speed") == "fast":
            settings["stability"] = 0.6
        elif user_preferences.get("voice_speed") == "slow":
            settings["stability"] = 0.9
            
        if user_preferences.get("voice_clarity") == "high":
            settings["similarity_boost"] = 0.9
        elif user_preferences.get("voice_clarity") == "low":
            settings["similarity_boost"] = 0.6
            
        return settings

    async def cleanup(self):
        """Cleanup resources"""
        await self.client.aclose()
        logger.info("🧹 ElevenLabs service cleaned up")


# Alternative STT service using OpenAI Whisper (more reliable for STT)
class WhisperSTTService:
    """Alternative Speech-to-Text service using OpenAI Whisper"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.base_url = "https://api.openai.com/v1"
        
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            headers={
                "Authorization": f"Bearer {self.api_key}",
            }
        )
        
        if not self.api_key:
            logger.warning("⚠️ OpenAI API key not found. Whisper STT will be disabled.")
        else:
            logger.info("✅ Whisper STT service initialized")

    async def speech_to_text(self, audio_data: bytes, language: str = "en") -> Dict[str, Any]:
        """Convert speech to text using OpenAI Whisper"""
        if not self.api_key:
            raise Exception("OpenAI API key not configured")

        try:
            logger.info("🎧 Converting speech to text with Whisper", 
                       audio_size=len(audio_data))

            # Prepare multipart form data
            files = {
                "file": ("audio.mp3", io.BytesIO(audio_data), "audio/mpeg"),
            }
            
            data = {
                "model": "whisper-1",
                "language": language,
                "response_format": "json"
            }

            response = await self.client.post(
                f"{self.base_url}/audio/transcriptions",
                files=files,
                data=data
            )

            response.raise_for_status()
            result = response.json()
            
            logger.info("✅ Whisper speech-to-text completed")
            return {
                "text": result.get("text", ""),
                "language": language,
                "duration": result.get("duration", 0.0),
                "confidence": 0.9  # Whisper doesn't provide confidence, assume high
            }

        except Exception as e:
            logger.error("❌ Whisper speech-to-text failed", error=str(e))
            return {
                "text": "[Speech recognition failed]",
                "confidence": 0.0,
                "language": language,
                "duration": 0.0,
                "error": str(e)
            }

    async def cleanup(self):
        """Cleanup resources"""
        await self.client.aclose()
