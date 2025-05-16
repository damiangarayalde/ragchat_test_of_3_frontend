# backend/services/file_service.py
import os
import logging

logger = logging.getLogger(__name__)


class FileService:
    @staticmethod
    def safe_delete(path: str) -> bool:
        try:
            if os.path.exists(path):
                os.remove(path)
                return True
            return False
        except Exception as e:
            logger.error(f"File deletion failed: {str(e)}")
            return False

    @staticmethod
    def save_file(file_path: str, content: bytes) -> bool:
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "wb") as f:
                f.write(content)
            return True
        except Exception as e:
            logger.error(f"File save failed: {str(e)}")
            return False
