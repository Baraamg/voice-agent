from app.services.transcription import TranscriptionService
from app.services.nlp import NLPService
from app.services.database import DatabaseService
import logging
import asyncio

logger = logging.getLogger(__name__)

class VoiceProcessor:
    def __init__(self, db_service: DatabaseService):
        self.transcription_service = TranscriptionService()
        self.nlp_service = NLPService()
        self.db_service = db_service
    
    async def process_audio(self, insight_id: int, file_path: str) -> dict:
        """
        Complete processing pipeline for audio file
        """
        try:
            # Update status to processing
            self.db_service.update_insight(insight_id, processing_status="processing")
            
            # Step 1: Transcribe audio
            logger.info(f"Starting transcription for insight {insight_id}")
            transcription_result = await self.transcription_service.transcribe_audio(file_path)
            
            if not transcription_result["success"]:
                self.db_service.update_insight(
                    insight_id, 
                    processing_status="failed",
                    transcription=f"Transcription failed: {transcription_result.get('error', 'Unknown error')}"
                )
                return {"success": False, "error": "Transcription failed"}
            
            # Step 2: Analyze transcribed text
            logger.info(f"Starting NLP analysis for insight {insight_id}")
            nlp_result = await self.nlp_service.analyze_text(transcription_result["text"])
            
            # Step 3: Update database with results
            update_data = {
                "transcription": transcription_result["text"],
                "language": nlp_result.get("language", transcription_result.get("language", "unknown")),
                "topic": nlp_result.get("topic", ""),
                "sentiment": nlp_result.get("sentiment", "neutral"),
                "action_items": nlp_result.get("action_items", []),
                "summary": nlp_result.get("summary", "") or "No summary available",
                "confidence_score": nlp_result.get("confidence_score", 0.0),
                "processing_status": "completed" if nlp_result.get("success", False) else "failed"
            }
            
            updated_insight = self.db_service.update_insight(insight_id, **update_data)
            
            logger.info(f"Processing completed for insight {insight_id}")
            
            return {
                "success": True,
                "insight": updated_insight.to_dict() if updated_insight else None
            }
            
        except Exception as e:
            logger.error(f"Processing failed for insight {insight_id}: {str(e)}")
            self.db_service.update_insight(
                insight_id, 
                processing_status="failed",
                transcription=f"Processing failed: {str(e)}"
            )
            return {"success": False, "error": str(e)}