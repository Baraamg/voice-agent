import os
import uuid
from pathlib import Path
from app.config import settings

class FileHandler:
    @staticmethod
    def save_uploaded_file(file, upload_folder: str = settings.UPLOAD_FOLDER) -> str:
        """Save uploaded file and return the file path"""
        # Create upload folder if it doesn't exist
        Path(upload_folder).mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename
        file_extension = Path(file.filename).suffix
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(upload_folder, unique_filename)
        
        # Save file
        with open(file_path, "wb") as buffer:
            content = file.file.read()
            buffer.write(content)
        
        return file_path
    
    @staticmethod
    def validate_file(filename: str) -> bool:
        """Validate file extension"""
        file_extension = Path(filename).suffix.lower()
        return file_extension in settings.ALLOWED_EXTENSIONS
    
    @staticmethod
    def get_file_size(file_path: str) -> int:
        """Get file size in bytes"""
        return os.path.getsize(file_path)