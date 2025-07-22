from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
import os
import logging
import json

from app.config import settings
from app.services.database import get_db, create_tables, DatabaseService
from app.services.voice_processor import VoiceProcessor
from app.utils.file_handler import FileHandler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="VoiceAgent API",
    description="Voice-to-Insight System",
    version="1.0.0"
)

# Create required directories if they don't exist
required_dirs = ["static", "uploads", "data", "templates"]
for directory in required_dirs:
    if not os.path.exists(directory):
        os.makedirs(directory)
        logger.info(f"Created directory: {directory}")

# Mount static files (only if directory exists)
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# Create database tables on startup
@app.on_event("startup")
async def startup_event():
    create_tables()
    logger.info("Database tables created")
    
    # Check API key on startup
    if not settings.GROQ_API_KEY or settings.GROQ_API_KEY == "your-groq-api-key-here":
        logger.warning("⚠️  GROQ_API_KEY is not set properly. Audio processing will fail.")
        logger.warning("Please get an API key from https://console.groq.com and update your .env file")

# Background task for processing audio
async def process_audio_background(insight_id: int, file_path: str, db: Session):
    """Background task to process audio file"""
    try:
        db_service = DatabaseService(db)
        processor = VoiceProcessor(db_service)
        result = await processor.process_audio(insight_id, file_path)
        logger.info(f"Background processing completed for insight {insight_id}: {result}")
    except Exception as e:
        logger.error(f"Background processing failed for insight {insight_id}: {str(e)}")
        # Update the insight with error status
        db_service = DatabaseService(db)
        db_service.update_insight(
            insight_id, 
            processing_status="failed",
            transcription=f"Processing failed: {str(e)}"
        )

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main HTML interface"""
    
    return f"""<!DOCTYPE html>
<html>
  <head><meta charset="utf-8"><title>Run Streamlit App</title></head>
  <body>
    <h2>How to open the website</h2>
    <p>1. In your project folder, open a terminal and run:</p>
    <pre>streamlit run streamlit_app.py --server.port 8501</pre>
    <p>2. In your browser go to: <code>http://localhost:8501</code></p>
  </body>
</html>
"""

@app.post("/upload_audio")
async def upload_audio(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload and process audio file"""
    try:
        # Check if API key is configured
        if not settings.GROQ_API_KEY or settings.GROQ_API_KEY == "your-groq-api-key-here":
            raise HTTPException(
                status_code=400, 
                detail="Groq API key not configured. Please set GROQ_API_KEY in your .env file."
            )
        
        # Validate file
        if not FileHandler.validate_file(file.filename):
            raise HTTPException(status_code=400, detail="Invalid file type. Supported: .wav, .mp3, .m4a")
        
        # Save file
        file_path = FileHandler.save_uploaded_file(file)
        
        # Check file size
        if FileHandler.get_file_size(file_path) > settings.MAX_FILE_SIZE:
            os.remove(file_path)
            raise HTTPException(status_code=400, detail="File too large")
        
        # Create database entry
        db_service = DatabaseService(db)
        insight = db_service.create_audio_insight(file.filename, file_path)
        
        # Start background processing
        background_tasks.add_task(process_audio_background, insight.id, file_path, db)
        
        return {
            "success": True,
            "message": "File uploaded successfully. Processing started.",
            "insight_id": insight.id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/insights/{insight_id}")
async def get_insight(insight_id: int, db: Session = Depends(get_db)):
    """Get insight by ID"""
    try:
        db_service = DatabaseService(db)
        insight = db_service.get_insight(insight_id)
        
        if not insight:
            raise HTTPException(status_code=404, detail="Insight not found")
        
        return insight.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving insight {insight_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/insights")
async def get_all_insights(db: Session = Depends(get_db)):
    """Get all insights"""
    try:
        db_service = DatabaseService(db)
        insights = db_service.get_all_insights()
        return [insight.to_dict() for insight in insights]
        
    except Exception as e:
        logger.error(f"Error retrieving insights: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/insights/{insight_id}")
async def delete_insight(insight_id: int, db: Session = Depends(get_db)):
    """Delete insight and associated file"""
    try:
        db_service = DatabaseService(db)
        insight = db_service.get_insight(insight_id)
        
        if not insight:
            raise HTTPException(status_code=404, detail="Insight not found")
        
        # Delete file if it exists
        if insight.file_path and os.path.exists(insight.file_path):
            os.remove(insight.file_path)
        
        # Delete from database
        db_service.delete_insight(insight_id)
        
        return {"success": True, "message": "Insight deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting insight {insight_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    api_key_configured = bool(settings.GROQ_API_KEY and settings.GROQ_API_KEY != "your-groq-api-key-here")
    
    return {
        "status": "healthy",
        "api_key_configured": api_key_configured,
        "database": "connected",
        "upload_directory": os.path.exists("uploads")
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)