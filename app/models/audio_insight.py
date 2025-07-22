from sqlalchemy import Column, Integer, String, DateTime, Text, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()

class AudioInsight(Base):
    __tablename__ = "audio_insights"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    transcription = Column(Text)
    topic = Column(String)
    sentiment = Column(String)
    language = Column(String)
    action_items = Column(Text)  # JSON string
    summary = Column(Text, nullable=False, server_default="")
    confidence_score = Column(Float)
    processing_status = Column(String, default="pending")  # pending, processing, completed, failed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def to_dict(self):
        import json
        action_items = []
        if self.action_items:
            try:
                action_items = json.loads(self.action_items)
            except:
                action_items = []
        
        return {
            "id": self.id,
            "filename": self.filename,
            "transcription": self.transcription,
            "topic": self.topic,
            "sentiment": self.sentiment,
            "language": self.language,
            "action_items": action_items,
            "summary": self.summary,
            "confidence_score": self.confidence_score,
            "processing_status": self.processing_status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }