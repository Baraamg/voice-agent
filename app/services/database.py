from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.models.audio_insight import Base, AudioInsight
from app.config import settings
import json

engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_tables():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class DatabaseService:
    def __init__(self, db: Session):
        self.db = db
    
    def create_audio_insight(self, filename: str, file_path: str) -> AudioInsight:
        insight = AudioInsight(
            filename=filename,
            file_path=file_path,
            processing_status="pending"
        )
        self.db.add(insight)
        self.db.commit()
        self.db.refresh(insight)
        return insight
    
    def update_insight(self, insight_id: int, **kwargs) -> AudioInsight:
        insight = self.db.query(AudioInsight).filter(AudioInsight.id == insight_id).first()
        if insight:
            for key, value in kwargs.items():
                if key == "action_items" and isinstance(value, list):
                    value = json.dumps(value)
                setattr(insight, key, value)
            self.db.commit()
            self.db.refresh(insight)
        return insight
    
    def get_insight(self, insight_id: int) -> AudioInsight:
        return self.db.query(AudioInsight).filter(AudioInsight.id == insight_id).first()
    
    def get_all_insights(self) -> list[AudioInsight]:
        return self.db.query(AudioInsight).all()
    
    def update_insight(self, insight_id: int, **kwargs) -> AudioInsight:
        insight = self.db.query(AudioInsight).filter(AudioInsight.id == insight_id).first()
        if insight:
            for key, value in kwargs.items():
                if key == "action_items" and isinstance(value, list):
                    value = json.dumps(value)
                if hasattr(insight, key):  # Only set attributes that exist
                    setattr(insight, key, value)
            self.db.commit()
            self.db.refresh(insight)
        return insight