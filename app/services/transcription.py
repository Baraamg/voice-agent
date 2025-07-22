import os
import logging
import httpx
from groq import Groq
from app.config import settings

logger = logging.getLogger(__name__)

class TranscriptionService:
    def __init__(self):
        """Initialize the TranscriptionService with Groq client"""
        if not settings.GROQ_API_KEY:
            logger.error("GROQ_API_KEY is not set")
            raise ValueError("Please set your GROQ_API_KEY in .env file")
        
        try:
            self.client = Groq(api_key=settings.GROQ_API_KEY)
            logger.info("Groq client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Groq client: {e}")
            raise

    async def transcribe_audio(self, file_path: str) -> dict:
        """
        Transcribe audio file using Groq Whisper API
        
        Args:
            file_path (str): Path to the audio file to transcribe
            
        Returns:
            dict: Transcription result with format:
            {
                "success": bool,
                "text": str,
                "language": str,
                "duration": float,
                "error": str (optional)
            }
        """
        try:
            logger.info(f"Starting transcription for file: {file_path}")
            
            # Validate file existence and size
            if not os.path.exists(file_path):
                msg = f"File not found: {file_path}"
                logger.error(msg)
                return {"success": False, "error": msg}
            
            file_size = os.path.getsize(file_path)
            if file_size > 25 * 1024 * 1024:  # 25MB limit
                msg = "File too large for transcription (max 25MB)"
                logger.error(msg)
                return {"success": False, "error": msg}
            
            # Read and transcribe file
            with open(file_path, "rb") as audio_file:
                file_content = audio_file.read()
                
                try:
                    # Primary transcription attempt
                    logger.info("Attempting primary transcription")
                    response = self.client.audio.transcriptions.create(
                        file=(os.path.basename(file_path), file_content),
                        model="whisper-large-v3",
                        response_format="text",
                        language="en",
                        temperature=0.2
                    )
                    
                    logger.info("Transcription completed successfully")
                    return {
                        "success": True,
                        "text": response,
                        "language": "en",
                        "duration": None,
                        "confidence_score": 0.95
                    }
                    
                except Exception as api_error:
                    logger.error(f"Primary transcription failed: {str(api_error)}")
                    
                    try:
                        # Fallback transcription attempt
                        logger.info("Attempting fallback transcription")
                        response = self.client.audio.transcriptions.create(
                            file=(os.path.basename(file_path), file_content),
                            model=settings.WHISPER_MODEL,
                            response_format="text",
                            language="en",
                            temperature=0.0
                        )
                        
                        return {
                            "success": True,
                            "text": response,
                            "language": "en",
                            "confidence_score": 0.8
                        }
                        
                    except Exception as fallback_error:
                        msg = f"Fallback transcription failed: {str(fallback_error)}"
                        logger.error(msg)
                        return {"success": False, "error": msg}
                    
        except Exception as e:
            msg = f"Transcription process failed: {str(e)}"
            logger.error(msg)
            return {"success": False, "error": msg}