import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # Groq API Configuration
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "your-groq-api-key-here")
    
    # Database Configuration
    DATABASE_URL = "sqlite:///./voiceagent.db"
    
    # File Storage
    UPLOAD_FOLDER = "uploads"
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS = {'.wav', '.mp3', '.m4a'}
    
    # API Configuration
    API_HOST = "0.0.0.0"
    API_PORT = 8000
    
    # Whisper Model Configuration
    WHISPER_MODEL = "whisper-large-v3"
    
    # LLM Configuration
    LLM_MODEL = "llama-3.1-70b-versatile"  # Updated to the latest supported model

settings = Settings()